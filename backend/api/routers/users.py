from fastapi import APIRouter, Depends

from core.security import get_current_user
from database.subscription_store import SubscriptionStore
from core.plan_models import PLAN_MODELS, Plan

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me")
def me(
    user = Depends(get_current_user),
    subs_store: SubscriptionStore = Depends()
):
    sub = subs_store.get_by_user_id(user.id)

    if not sub:
        return {
            "user": user.email,
            "plan": None,
            "status": "inactive",
            "models_allowed": []
        }

    plan = Plan(sub["plan"])

    return {
        "user": user.email,
        "plan": plan.value,
        "status": sub["status"],
        "models_allowed": list(PLAN_MODELS[plan])
    }
