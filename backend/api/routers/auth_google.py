# backend/api/routers/auth_google.py
from fastapi import APIRouter, HTTPException, Depends
from google.oauth2 import id_token
from google.auth.transport import requests
from sqlalchemy.orm import Session

from backend.api.db_deps import get_db
from backend.database.models.user import User
from backend.api.schemas.auth import GoogleAuthRequest, AuthResponse
from backend.api.security.jwt import create_access_token
from backend.core.config import settings
from backend.services.subscription_service import get_active_subscription

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/google", response_model=AuthResponse)
def google_login(payload: GoogleAuthRequest, db: Session = Depends(get_db)):
    try:
        idinfo = id_token.verify_oauth2_token(
            payload.id_token,
            requests.Request(),
            settings.GOOGLE_OAUTH_CLIENT_ID
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    email = idinfo["email"]
    sub = idinfo["sub"]

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            device_id=payload.device_id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Política un dispositivo
    if user.device_id and user.device_id != payload.device_id:
        raise HTTPException(
            status_code=409,
            detail={"error": "DEVICE_MISMATCH", "message": "Esta cuenta ya está vinculada a otro dispositivo."},
        )

    if not user.device_id:
        user.device_id = payload.device_id
        db.commit()

    subscription = get_active_subscription(db, user_id=user.id, device_id=payload.device_id)
    current_plan = subscription.plan_id if subscription else "no_plan"

    token = create_access_token(
        sub=sub,
        user_id=user.id,
        email=user.email,
        device_id=payload.device_id,
        plan=current_plan,
    )

    return AuthResponse(access_token=token)