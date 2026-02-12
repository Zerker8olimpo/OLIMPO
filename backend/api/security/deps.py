from fastapi import Security, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from backend.api.db_deps import get_db
from backend.api.security.jwt import verify_token
from backend.core.config import settings
from backend.database.models.payment import Payment
from backend.database.models.subscription import Subscription
from backend.database.models.user import User
from backend.core.plans import PLANS, PLAN_MODEL_MAP

logger = logging.getLogger("olimpo.billing")

bearer_scheme = HTTPBearer(auto_error=True)

def get_active_subscription(db: Session, user_id: int):
    """
    Busca la suscripción activa más reciente para un usuario que no haya expirado.
    """
    return (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user_id,
            Subscription.status == "active",
            Subscription.end_date > datetime.utcnow(),
        )
        .order_by(Subscription.end_date.desc())
        .first()
    )

def validate_billing_policy(sub: Subscription, claims: dict, expected_provider: str):
    """
    PolicyAgent Centralizado: Valida integridad y estado de la suscripción.
    Permite bypass de estados si test_mode es True.
    """
    # PAL DEV BYPASS
    if settings.POLICY_MODE == "dev" or settings.DEV_BYPASS_POLICIES:
        return

    is_test_mode = claims.get("test_mode") is True
    is_sandbox = settings.MP_ENV == "sandbox"

    # 1. Validaciones de Integridad (SIEMPRE)
    if sub.user_id != int(claims.get("user_id")):
        raise HTTPException(status_code=403, detail="USER_MISMATCH")
    if sub.device_id != claims.get("device_id"):
        raise HTTPException(status_code=403, detail="DEVICE_MISMATCH")
    if sub.provider != expected_provider:
        logger.warning(
            f"[BILLING_POLICY] PROVIDER_MISMATCH | "
            f"User: {claims.get('user_id')} | "
            f"SubID: {sub.id} | "
            f"Device: {claims.get('device_id')} | "
            f"Expected: {expected_provider} | "
            f"Actual: {sub.provider} | "
            f"TestMode: {is_test_mode}"
        )
        raise HTTPException(status_code=403, detail="PROVIDER_MISMATCH")

    if is_test_mode:
        return  # Bypass de políticas de entorno/estado

    # 2. Políticas de Entorno/Estado
    if not is_sandbox:
        if sub.status != "active":
            raise HTTPException(status_code=403, detail="PRODUCTION_REQUIRES_ACTIVE_SUBSCRIPTION")
    else:
        if sub.status not in ("pending", "active"):
            raise HTTPException(status_code=403, detail="SANDBOX_REQUIRES_PENDING_OR_ACTIVE_SUBSCRIPTION")

def activate_subscription_logic(
    db: Session,
    subscription: Subscription,
    provider: str,
    payment_ref: str,
    amount: int = 0,
    currency: str = "CLP",
    start_date: datetime = None,
    end_date: datetime = None,
    auto_renew: bool = True
):
    """
    Lógica única y normalizada para activar suscripciones.
    Implementa idempotencia verificando el payment_ref.
    """
    # 1. Idempotencia: Verificar si este pago ya fue procesado
    existing_payment = db.query(Payment).filter(
        Payment.external_id == payment_ref,
        Payment.status == "approved"
    ).first()
    if existing_payment:
        return subscription

    # 2. Actualizar Suscripción
    subscription.status = "active"
    subscription.provider = provider
    subscription.external_reference = payment_ref
    subscription.start_date = start_date or datetime.utcnow()
    subscription.end_date = end_date or (subscription.start_date + timedelta(days=30))
    subscription.auto_renew = auto_renew

    # 3. Actualizar o Crear Registro de Pago
    payment = db.query(Payment).filter(
        Payment.subscription_id == subscription.id,
        Payment.provider == provider,
        Payment.status == "created"
    ).first()

    if not payment:
        payment = Payment(user_id=subscription.user_id, subscription_id=subscription.id, provider=provider, amount=amount, currency=currency)
        db.add(payment)

    payment.status = "approved"
    payment.external_id = payment_ref
    db.commit()
    return subscription

def get_current_claims(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: Session = Depends(get_db)
) -> dict:
    """
    Valida el token JWT y asegura que contenga los claims obligatorios.
    """
    token = credentials.credentials
    claims = verify_token(token)

    REQUIRED = ["user_id", "email", "device_id", "plan"]
    for field in REQUIRED:
        if field not in claims:
            raise HTTPException(status_code=401, detail="INVALID_TOKEN_CLAIMS")

    return claims

def require_model_access(model_name: str):
    """
    Genera una dependencia que valida si el usuario tiene acceso al modelo solicitado.
    ESTRATEGIA: DB-First (Más seguro que JWT claims para evitar race conditions en expiración).
    """
    def _access_checker(
        claims: dict = Depends(get_current_claims),
        db: Session = Depends(get_db)
    ):
        user_id = claims.get("user_id")
        device_id = claims.get("device_id")

        # Consultar fuente de verdad (DB)
        sub = get_active_subscription(db, user_id)
        
        # Validar existencia y propiedad del dispositivo
        if not sub or sub.device_id != device_id:
             # Fallback: Si no hay sub activa, asumimos plan 'basic' (si aplica) o denegamos
             # Para modelos premium, denegamos.
             current_plan = "basic"
        else:
             current_plan = sub.plan_id

        allowed_models = PLAN_MODEL_MAP.get(current_plan, [])
        
        if model_name not in allowed_models:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "PLAN_RESTRICTION",
                    "message": f"Tu plan actual ({current_plan}) no permite el acceso al modelo {model_name}.",
                    "action": "UPGRADE_PLAN"
                }
            )
        return claims
    return _access_checker
