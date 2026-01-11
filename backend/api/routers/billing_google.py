# backend/api/routers/billing_google.py
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.db_deps import get_db
from backend.api.security.deps import get_current_claims
from backend.database.models.user import User
from backend.database.models.subscription import Subscription
from backend.database.models.payment import Payment
from backend.core.email_service import send_subscription_active_email


router = APIRouter(prefix="/billing/google", tags=["billing-google"])


class GoogleVerifyRequest(BaseModel):
    purchase_token: str
    product_id: str  # e.g. olimpo_pro_monthly
    device_id: str = Field(..., description="Android Device ID único para vincular la cuenta")


def _map_product_to_plan(product_id: str) -> str:
    mapping = {
        "olimpo_basic_monthly": "basic",
        "olimpo_pro_monthly": "pro",
        "olimpo_enterprise_monthly": "enterprise",
    }
    return mapping.get(product_id, "")


def _map_product_to_price(product_id: str) -> int:
    mapping = {
        "olimpo_basic_monthly": 0,      # Ajustar precios reales
        "olimpo_pro_monthly": 10000,    # Ejemplo CLP
        "olimpo_enterprise_monthly": 50000,
    }
    return mapping.get(product_id, 0)

@router.post("/verify")
def google_verify(
    payload: GoogleVerifyRequest,
    claims: dict = Depends(get_current_claims),
    db: Session = Depends(get_db),
):
    email = claims.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="INVALID_TOKEN_CLAIMS")

    plan = _map_product_to_plan(payload.product_id)
    if not plan:
        raise HTTPException(status_code=400, detail="UNKNOWN_PRODUCT_ID")

    # ============================================================
    # TODO: Verificación REAL con Google Play Developer API
    # - Validar purchase_token/product_id/package_name
    # - Obtener expiryTimeMillis
    # - Detectar cancel/refund
    # ============================================================

    user = db.query(User).filter(User.email == email).one_or_none()
    if not user:
        # Si hoy tu sistema no crea User por Google, esto evita fallo.
        # Idealmente, tu /auth/google debería crear/asegurar el usuario.
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")

    # --- POLÍTICA DE UN SOLO DISPOSITIVO ---
    # Verificamos si el usuario ya tiene un dispositivo vinculado.
    # Nota: Esto asume que tu modelo User tiene un campo 'device_id'.
    # Si no existe el campo en la DB, usamos hasattr para no romper el código, pero deberías agregarlo.
    if hasattr(user, "device_id"):
        if user.device_id and user.device_id != payload.device_id:
            # El usuario intenta pagar/usar desde otro dispositivo distinto al registrado
            raise HTTPException(status_code=409, detail="DEVICE_MISMATCH: Cuenta vinculada a otro dispositivo.")
        
        if not user.device_id:
            # Primera vez: vinculamos este dispositivo a la cuenta
            user.device_id = payload.device_id
            db.add(user)

    sub = db.query(Subscription).filter(Subscription.user_id == user.id).one_or_none()
    
    # --- CÁLCULO DE VIGENCIA (30 DÍAS) ---
    now = datetime.utcnow()
    
    if not sub:
        # Suscripción nueva: 30 días desde hoy
        start_date = now
        end_date = now + timedelta(days=30)
        
        sub = Subscription(
            user_id=user.id,
            plan=plan,
            status="active",
            provider="google",
            external_reference=payload.purchase_token,
            start_date=start_date,
            end_date=end_date,
            auto_renew=True,
        )
        db.add(sub)
    else:
        # Renovación: Sumar 30 días a la fecha actual de vencimiento (si es futura)
        # o desde hoy (si ya venció).
        if sub.end_date and sub.end_date > now:
            new_start = sub.end_date
        else:
            new_start = now
            
        new_end = new_start + timedelta(days=30)
        
        sub.plan = plan
        sub.status = "active"
        sub.provider = "google"
        sub.external_reference = payload.purchase_token
        # Mantenemos la fecha de inicio original si es renovación continua, o reseteamos si venció
        if sub.status != "active":
            sub.start_date = now
            
        sub.end_date = new_end
        sub.auto_renew = True

    # Registrar pago (opcional, pero recomendado)
    db.add(Payment(
        user_id=user.id,
        provider="google",
        amount=_map_product_to_price(payload.product_id),
        currency="CLP",
        status="approved",
        external_id=payload.purchase_token,
    ))

    db.commit()

    # --- NOTIFICACIÓN POR CORREO ---
    expires_str = sub.end_date.strftime("%Y-%m-%d") if sub.end_date else "Indefinido"
    send_subscription_active_email(user.email, sub.plan, expires_str)

    return {
        "status": "active",
        "plan": sub.plan,
        "provider": sub.provider,
        "expires_at": sub.end_date.isoformat() if sub.end_date else None
    }
