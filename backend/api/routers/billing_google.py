# backend/api/routers/billing_google.py
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.db_deps import get_db
from backend.api.security.deps import get_current_claims
from backend.database.models.user import User
from backend.database.models.subscription import Subscription
from backend.database.models.payment import Payment


router = APIRouter(prefix="/billing/google", tags=["billing-google"])


class GoogleVerifyRequest(BaseModel):
    purchase_token: str
    product_id: str  # e.g. olimpo_pro_monthly


def _map_product_to_plan(product_id: str) -> str:
    mapping = {
        "olimpo_basic_monthly": "basic",
        "olimpo_pro_monthly": "pro",
        "olimpo_enterprise_monthly": "enterprise",
    }
    return mapping.get(product_id, "")


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

    # Stub operativo: activa 30 días (solo para que puedas probar end-to-end)
    start = datetime.utcnow()
    end = start + timedelta(days=30)

    user = db.query(User).filter(User.email == email).one_or_none()
    if not user:
        # Si hoy tu sistema no crea User por Google, esto evita fallo.
        # Idealmente, tu /auth/google debería crear/asegurar el usuario.
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")

    sub = db.query(Subscription).filter(Subscription.user_id == user.id).one_or_none()
    if not sub:
        sub = Subscription(
            user_id=user.id,
            plan=plan,
            status="active",
            provider="google",
            external_reference=payload.purchase_token,
            start_date=start,
            end_date=end,
            auto_renew=True,
        )
        db.add(sub)
    else:
        sub.plan = plan
        sub.status = "active"
        sub.provider = "google"
        sub.external_reference = payload.purchase_token
        sub.start_date = start
        sub.end_date = end
        sub.auto_renew = True

    # Registrar pago (opcional, pero recomendado)
    db.add(Payment(
        user_id=user.id,
        provider="google",
        amount=0,          # En Google Play el monto lo puedes registrar vía config o metadata
        currency="CLP",
        status="approved",
        external_id=payload.purchase_token,
    ))

    db.commit()

    return {
        "status": "active",
        "plan": sub.plan,
        "provider": sub.provider,
        "expires_at": sub.end_date.isoformat() if sub.end_date else None
    }
