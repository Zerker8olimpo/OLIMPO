from fastapi import Header, HTTPException, Depends, status
from sqlalchemy.orm import Session
from datetime import datetime

from backend.api.db_deps import get_db
from backend.api.security.jwt import verify_token
from backend.database.models.subscription import Subscription
from backend.database.models.user import User
from backend.core.plans import PLANS

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

def get_current_claims(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db)
) -> dict:
    """
    Lee Authorization: Bearer <olimpo_jwt>
    Retorna claims: {"sub": "...", "email": "...", ...}
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="MISSING_BEARER_TOKEN")

    token = authorization.replace("Bearer ", "", 1).strip()
    if not token:
        raise HTTPException(status_code=401, detail="EMPTY_TOKEN")

    claims = verify_token(token)
    user_id = claims.get("user_id")

    # Fallback: Si user_id no está en el token, lo resolvemos por email
    if user_id is None:
        email = claims.get("email")
        if email:
            user = db.query(User).filter(User.email == email).first()
            if user:
                user_id = user.id
                # Inyectamos para que el resto de la cadena lo tenga disponible
                claims["user_id"] = user_id

    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload: user_id not found")

    subscription = get_active_subscription(db, int(user_id))

    if subscription:
        plan = subscription.plan
        plan_cfg = PLANS.get(plan)
        
        claims["plan"] = plan
        claims["models"] = plan_cfg["models"] if plan_cfg else []
        claims["subscription_expires_at"] = subscription.end_date.isoformat()
    else:
        # Usuario autenticado pero sin plan activo
        claims["plan"] = None
        claims["models"] = []
        claims["subscription_expires_at"] = None

    return claims

def require_model_access(model_name: str):
    """
    Genera una dependencia que valida si el usuario tiene acceso al modelo solicitado.
    """
    def _access_checker(claims: dict = Depends(get_current_claims)):
        if model_name not in claims.get("models", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "PLAN_RESTRICTION",
                    "message": f"Tu plan actual ({claims.get('plan')}) no permite el acceso al modelo {model_name}.",
                    "action": "UPGRADE_PLAN"
                }
            )
        return claims
    return _access_checker
