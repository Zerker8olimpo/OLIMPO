# backend/api/routers/billing_google.py
from datetime import datetime, timedelta
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
from backend.core.plans import PLANS
from backend.database.models.subscription import Subscription
from backend.database.models.payment import Payment
from backend.core.email_service import send_subscription_active_email


router = APIRouter(prefix="/billing/google", tags=["billing-google"])


class GoogleVerifyRequest(BaseModel):
    purchase_token: str
    product_id: str  # e.g. olimpo_pro_monthly
    subscription_id: int


def _map_product_to_plan(product_id: str) -> str:
    mapping = {
        "olimpo_basic_monthly": "basic",
        "olimpo_pro_monthly": "pro",
        "olimpo_enterprise_monthly": "enterprise",
    }
    return mapping.get(product_id, "")


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


@router.post("/verify")
def google_verify(
    payload: GoogleVerifyRequest,
    claims: dict = Depends(get_current_claims),
    db: Session = Depends(get_db),
):
    email = claims.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="INVALID_TOKEN_CLAIMS")

    device_id = claims.get("device_id")
    plan = _map_product_to_plan(payload.product_id)
    if not plan:
        raise HTTPException(status_code=400, detail="UNKNOWN_PRODUCT_ID")

    # 2. Verificación (Test vs Real)
    is_test_mode = claims.get("test_mode") is True
    
    if is_test_mode:
        # Simulación
        start = datetime.utcnow()
        end = start + PLANS[plan]["duration"]
    else:
        # Validación REAL
        google_data = verify_with_google_play(payload.product_id, payload.purchase_token)
        # Google devuelve timestamps en milisegundos como strings
        start = datetime.utcfromtimestamp(int(google_data['startTimeMillis']) / 1000.0)
        end = datetime.utcfromtimestamp(int(google_data['expiryTimeMillis']) / 1000.0)

    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Si hoy tu sistema no crea User por Google, esto evita fallo.
        # Idealmente, tu /auth/google debería crear/asegurar el usuario.
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")

    sub = (
        db.query(Subscription)
        .filter(
            Subscription.id == payload.subscription_id,
            Subscription.user_id == user.id,
            Subscription.device_id == device_id
        )
        .order_by(Subscription.created_at.desc())
        .first()
    )

    if not sub:
        raise HTTPException(status_code=404, detail="SUBSCRIPTION_NOT_FOUND")

    # Validar política de facturación (PolicyAgent)
    # En Google Pay, el intent debe haber sido creado con provider="google"
    validate_billing_policy(sub, claims, "google")

    # 3. Activación Normalizada
    activate_subscription_logic(
        db=db,
        subscription=sub,
        provider="google",
        payment_ref=payload.purchase_token,
        amount=PLANS[plan]["price"],
        start_date=start,
        end_date=end,
        auto_renew=google_data.get("autoRenewing", True) if not is_test_mode else True
    )

    # Enviar correo de confirmación
    try:
        end_date_str = sub.end_date.strftime("%d/%m/%Y") if sub.end_date else "N/A"
        send_subscription_active_email(user.email, sub.plan_id, end_date_str)
    except Exception:
        pass # No bloquear la respuesta si falla el correo

    return {
        "status": "active",
        "plan": sub.plan_id,
        "provider": sub.provider,
        "expires_at": sub.end_date.isoformat() if sub.end_date else None
    }