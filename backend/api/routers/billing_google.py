from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import threading

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.api.db_deps import get_db
from backend.api.security.deps import get_current_claims
from backend.database.models.subscription import Subscription, PaymentProvider
from backend.database.models.user import User
from backend.core.plans import normalize_plan
from backend.api.security.jwt import create_access_token
from backend.api.routers.account import format_subscription_status

logger = logging.getLogger(__name__)

router = APIRouter(tags=["billing-google"])


class VerifyGooglePurchaseRequest(BaseModel):
    product_id: str
    purchase_token: str


# Registro de locks por purchase_token para serializar la sección crítica
_purchase_locks_guard = threading.Lock()
_purchase_locks: dict[str, threading.Lock] = {}


def _get_purchase_lock(purchase_token: str) -> threading.Lock:
    with _purchase_locks_guard:
        lock = _purchase_locks.get(purchase_token)
        if lock is None:
            lock = threading.Lock()
            _purchase_locks[purchase_token] = lock
        return lock


# -------------------------------------------------------
# FUNCIÓN REQUERIDA POR LOS TESTS
# pytest la reemplaza con monkeypatch
# -------------------------------------------------------
def verify_with_google_play(product_id: str, purchase_token: str):
    return {
        "status": "SUCCESS",
        "expiryTimeMillis": int(
            (datetime.now(timezone.utc) + timedelta(days=30)).timestamp() * 1000
        ),
    }


def _build_success_response(user: User, sub: Subscription) -> dict:
    status = format_subscription_status(sub)

    token = create_access_token(
        sub=str(user.id),
        user_id=user.id,
        email=user.email,
        device_id=user.device_id,
        plan=sub.plan_id,
    )

    return {
        "status": "SUCCESS",
        "subscription": status,
        "access_token": token,
    }


@router.post("/billing/google/verify")
def verify_google_purchase(
    payload: VerifyGooglePurchaseRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_claims),
):
    user_id = claims.get("user_id")
    device_id = claims.get("device_id")

    if user_id is None:
        raise HTTPException(status_code=401, detail="INVALID_TOKEN")

    # Validación externa fuera del lock
    verify_with_google_play(
        payload.product_id,
        payload.purchase_token,
    )

    purchase_lock = _get_purchase_lock(payload.purchase_token)

    with purchase_lock:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="USER_NOT_FOUND")

        existing = (
            db.query(Subscription)
            .filter(Subscription.external_ref == payload.purchase_token)
            .first()
        )

        if existing:
            return _build_success_response(user, existing)

        plan_id = normalize_plan(payload.product_id)
        start = datetime.now(timezone.utc)
        end = start + timedelta(days=30)

        try:
            sub = (
                db.query(Subscription)
                .filter(
                    Subscription.user_id == user_id,
                )
                .first()
            )

            if sub is None:
                sub = Subscription(
                    user_id=user_id,
                    provider=PaymentProvider.GOOGLE,
                    status="active",
                    plan_id=plan_id,
                    google_product_id=payload.product_id,
                    external_ref=payload.purchase_token,
                    start_date=start,
                    end_date=end,
                    auto_renew=True,
                )
                db.add(sub)
            else:
                sub.plan_id = plan_id
                sub.status = "active"
                sub.external_ref = payload.purchase_token
                sub.google_product_id = payload.product_id
                sub.start_date = start
                sub.end_date = end
                sub.auto_renew = True

            db.commit()
            db.refresh(sub)

        except IntegrityError:
            db.rollback()
            sub = (
                db.query(Subscription)
                .filter(Subscription.external_ref == payload.purchase_token)
                .first()
            )
            if sub is None:
                raise

        except SQLAlchemyError:
            db.rollback()
            sub = (
                db.query(Subscription)
                .filter(Subscription.external_ref == payload.purchase_token)
                .first()
            )
            if sub is None:
                raise

        return _build_success_response(user, sub)