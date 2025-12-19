# backend/core/errors.py
class DeviceConflictError(Exception):
    pass

from fastapi import HTTPException, status

class PlanNotAllowedError(HTTPException):
    def __init__(self, model: str, plan: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "PLAN_NOT_ALLOWED",
                "message": f"Model '{model}' not allowed for plan '{plan}'"
            }
        )

class SubscriptionInactiveError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "SUBSCRIPTION_INACTIVE",
                "message": "Subscription is inactive"
            }
        )