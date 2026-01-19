from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.db_deps import get_db
from backend.database.models.user import User
from backend.database.models.subscription import Subscription
from backend.database.models.device import Device
from backend.api.security.jwt import verify_google_id_token
from backend.observatory.services.observatory_service import observatory_service

router = APIRouter(prefix="/account", tags=["account"])

# ============================================================
# SCHEMAS
# ============================================================

class EvaluateRequest(BaseModel):
    gmail: str
    device_id: str
    app_version: str
    platform: str
    id_token: str  # Necesario para verificar identidad en cada evaluación

class AccountInfo(BaseModel):
    exists: bool
    gmail: str

class SubscriptionInfo(BaseModel):
    status: str  # none | active | expired
    plan: str    # basic | pro | enterprise | none
    days_remaining: int

class DeviceInfo(BaseModel):
    is_this_device: bool
    has_other_active_device: bool

class Flags(BaseModel):
    allow_app: bool
    require_device_decision: bool
    allow_reset_device: bool
    require_subscription: bool

class EvaluateResponse(BaseModel):
    account: AccountInfo
    subscription: SubscriptionInfo
    device: DeviceInfo
    flags: Flags

# ============================================================
# ENDPOINT
# ============================================================

@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate_account(
    data: EvaluateRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # 1. Verificación de Identidad (Stateless)
    try:
        user_info = verify_google_id_token(data.id_token)
        if user_info.get("email") != data.gmail:
            raise HTTPException(status_code=403, detail="Token email mismatch")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid identity: {str(e)}")

    # 2. Obtener o Crear Usuario (Idempotente)
    user = db.query(User).filter(User.email == data.gmail).first()
    if not user:
        user = User(email=data.gmail, is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)

    # 3. Lógica de Dispositivo
    # Regla: 1 cuenta = 1 dispositivo activo.
    active_device = db.query(Device).filter(Device.user_id == user.id, Device.is_active == True).first()
    
    is_this_device = False
    has_other_active_device = False

    if not active_device:
        # Si no hay dispositivo activo, vinculamos este automáticamente
        new_device = Device(user_id=user.id, device_uuid=data.device_id, platform=data.platform, is_active=True)
        db.add(new_device)
        db.commit()
        is_this_device = True
    else:
        if active_device.device_uuid == data.device_id:
            is_this_device = True
            # Actualizar last_seen
            active_device.last_seen = datetime.utcnow()
            db.commit()
        else:
            is_this_device = False
            has_other_active_device = True

    # 4. Lógica de Suscripción
    sub = db.query(Subscription).filter(Subscription.user_id == user.id, Subscription.status == "active").first()
    
    sub_status = "none"
    sub_plan = "none"
    days_remaining = 0

    if sub:
        if sub.end_date and sub.end_date < datetime.utcnow():
            sub.status = "expired"
            db.commit()
            sub_status = "expired"
            sub_plan = sub.plan
        else:
            sub_status = "active"
            sub_plan = sub.plan
            days_remaining = (sub.end_date - datetime.utcnow()).days if sub.end_date else 30

    # 5. Cálculo de Flags
    response = EvaluateResponse(
        account=AccountInfo(exists=True, gmail=data.gmail),
        subscription=SubscriptionInfo(status=sub_status, plan=sub_plan, days_remaining=days_remaining),
        device=DeviceInfo(is_this_device=is_this_device, has_other_active_device=has_other_active_device),
        flags=Flags(
            allow_app=(is_this_device and sub_status == "active"),
            require_device_decision=has_other_active_device,
            allow_reset_device=has_other_active_device,
            require_subscription=(sub_status != "active")
        )
    )

    # 6. Observatorio (Side-Channel / Fail-Open)
    background_tasks.add_task(
        observatory_service.observe_execution,
        context={
            "gmail": data.gmail,
            "device_id": data.device_id,
            "platform": data.platform,
            "app_version": data.app_version,
            "timestamp": datetime.utcnow().isoformat()
        },
        inputs=data.dict(exclude={"id_token"}),  # Excluir credenciales sensibles
        outputs=response.dict(),
        model_name="account_evaluation"
    )

    return response