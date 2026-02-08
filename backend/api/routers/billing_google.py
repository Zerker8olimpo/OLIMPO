# backend/api/routers/billing_google.py
from datetime import datetime, timedelta
import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from google.oauth2 import service_account
from googleapiclient.discovery import build

from backend.api.db_deps import get_db
from backend.api.security.deps import get_current_claims, validate_billing_policy, activate_subscription_logic
from backend.core.config import settings
from backend.database.models.user import User
from backend.core.plans import normalize_plan, PLAN_MODEL_MAP
from backend.database.models.subscription import Subscription
from backend.database.models.payment import Payment, PaymentProvider
from backend.core.email_service import send_subscription_active_email
from backend.api.security.jwt import create_access_token
from backend.api.routers.account import format_subscription_status

# Configuración de logs
logger = logging.getLogger(__name__)

# HARDENING: Lectura centralizada de la Public Key.
# Se valida en tiempo de importación (startup) para asegurar integridad del entorno.
GOOGLE_PLAY_PUBLIC_KEY = os.getenv("GOOGLE_PLAY_PUBLIC_KEY")
if not GOOGLE_PLAY_PUBLIC_KEY:
    raise RuntimeError("CRITICAL: GOOGLE_PLAY_PUBLIC_KEY environment variable is missing.")

router = APIRouter(tags=["billing-google"])


class VerifyGooglePurchaseRequest(BaseModel):
    product_id: str
    purchase_token: str


def verify_with_google_play(product_id: str, token: str):
    """
    Llamada real a Google Play Developer API.
    """
    if not settings.GOOGLE_PLAY_SERVICE_ACCOUNT_JSON:
        raise HTTPException(status_code=500, detail="GOOGLE_PLAY_SERVICE_ACCOUNT_NOT_CONFIGURED")

    scopes = ['https://www.googleapis.com/auth/androidpublisher']
    creds = service_account.Credentials.from_service_account_file(
        settings.GOOGLE_PLAY_SERVICE_ACCOUNT_JSON, scopes=scopes
    )
    service = build('androidpublisher', 'v3', credentials=creds)
    
    try:
        # Para suscripciones se usa purchases().subscriptions().get
        # Para productos consumibles se usa purchases().products().get
        request = service.purchases().subscriptions().get(
            packageName=settings.GOOGLE_PLAY_PACKAGE_NAME,
            subscriptionId=product_id,
            token=token
        )
        result = request.execute()
        # startTimeMillis, expiryTimeMillis, acknowledgementState, etc.
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Google Verification Failed: {str(e)}")


@router.post("/billing/google/verify")
@router.post("/payments/google/verify")
def verify_google_purchase(
    payload: VerifyGooglePurchaseRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_claims),
):
    user_id = claims.get("user_id")
    device_id = claims.get("device_id")
    
    # Recuperar usuario para generar token
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")

    # IDEMPOTENCIA: si ya existe purchase_token, retornar estado actual
    # Esto maneja reintentos de red o llamadas duplicadas del cliente sin error.
    existing_sub = db.query(Subscription).filter(
        Subscription.external_ref == payload.purchase_token
    ).first()
    if existing_sub:
        logger.info(f"[IDEMPOTENCY] Token {payload.purchase_token} already processed. Returning current status.")
        
        existing_status = format_subscription_status(existing_sub)

        new_token = create_access_token(
            sub=str(user.id),
            user_id=user.id,
            email=user.email,
            device_id=existing_sub.device_id,
            plan=existing_sub.plan_id,
        )

        return {
            "status": "SUCCESS",
            "subscription": existing_status,
            "access_token": new_token,
        }

    # Buscar suscripción existente por device_id/user_id para actualizarla
    sub = db.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.device_id == device_id
    ).order_by(Subscription.created_at.desc()).first()

    if not sub:
        # Crear nueva suscripción pendiente
        sub = Subscription(
            user_id=user_id,
            device_id=device_id,
            provider=PaymentProvider.GOOGLE,
            status="pending",
            plan_id="basic"
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)

    # Validar con Google Play
    # verify_with_google_play lanza HTTPException si falla
    google_data = verify_with_google_play(payload.product_id, payload.purchase_token)
    
    # Verificar que la suscripción esté activa (no expirada)
    expiry_ms = int(google_data.get('expiryTimeMillis', 0))
    if expiry_ms > 0:
        expiry_dt = datetime.utcfromtimestamp(expiry_ms / 1000.0)
        if expiry_dt < datetime.utcnow():
            logger.warning(f"[SUBSCRIPTION] Attempt to verify expired token for user {user_id}")
            raise HTTPException(status_code=400, detail="SUBSCRIPTION_EXPIRED")

    logger.info("[SUBSCRIPTION] Google Play subscription validated")

    plan_id = normalize_plan(payload.product_id)
    # Detectar cambio de plan (Upgrade/Downgrade)
    previous_plan = sub.plan_id

    # Actualizar suscripción
    sub.provider = PaymentProvider.GOOGLE
    sub.status = "active"
    sub.plan_id = plan_id
    sub.google_product_id = payload.product_id
    sub.external_ref = payload.purchase_token
    
    # Fechas desde Google
    if 'startTimeMillis' in google_data:
        sub.start_date = datetime.utcfromtimestamp(int(google_data['startTimeMillis']) / 1000.0)
    else:
        sub.start_date = datetime.utcnow()
        
    if 'expiryTimeMillis' in google_data:
        sub.end_date = datetime.utcfromtimestamp(int(google_data['expiryTimeMillis']) / 1000.0)
    else:
        sub.end_date = sub.start_date + timedelta(days=30)

    sub.auto_renew = google_data.get("autoRenewing", True)
    
    db.add(sub)
    db.commit()
    
    # Logs obligatorios para QA
    if previous_plan != plan_id and sub.created_at < datetime.utcnow() - timedelta(seconds=10):
        logger.info(f"[SUBSCRIPTION] user_id={user_id} upgraded plan={plan_id}")
    else:
        logger.info(f"[SUBSCRIPTION] user_id={user_id} plan={plan_id} active=true")

    logger.info(f"[SESSION] JWT issued with plan={plan_id} models={PLAN_MODEL_MAP.get(plan_id, [])}")

    status = format_subscription_status(sub)
    
    # Capa de compatibilidad: Asegurar contrato unificado
    status["models"] = status.get("models_enabled", [])
    status["models_enabled"] = status.get("models_enabled", [])
    status["active"] = status.get("has_active_plan", False)

    new_token = create_access_token(
        sub=str(user.id),
        user_id=user.id,
        email=user.email,
        device_id=sub.device_id,
        plan=sub.plan_id,
    )

    # RESPUESTA AUTORITATIVA DE SESIÓN
    return {
        "status": "SUCCESS",
        "subscription": status,
        "access_token": new_token,
    }