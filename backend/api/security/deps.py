# backend/api/security/deps.py
from __future__ import annotations

from datetime import datetime, timedelta
import logging
import os
from typing import Dict, List

import requests
from fastapi import Security, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.api.db_deps import get_db
from backend.api.security.jwt import verify_token
from backend.core.config import settings
from backend.database.models.payment import Payment, PaymentProvider
from backend.database.models.subscription import Subscription
from backend.database.models.user import User
from backend.services.subscription_service import (
    get_active_subscription,
    get_entitlements_for_plan,
    resolve_plan,
)

logger = logging.getLogger("olimpo.billing")

bearer_scheme = HTTPBearer(auto_error=True)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ============================================================
# AUTH / SESSION
# ============================================================

def get_current_claims(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> dict:
    """
    Valida JWT y asegura claims mínimos.
    """
    token = credentials.credentials
    claims = verify_token(token)

    required = ["user_id", "email", "device_id"]

    for field in required:
        if field not in claims:
            raise HTTPException(
                status_code=401,
                detail="INVALID_TOKEN_CLAIMS"
            )

    return claims


# Timeout para la verificación de tokens de Supabase en get_current_claims_web_or_app.
#
# El cliente supabase-py (fijado en requirements.txt) no expone forma de configurar
# el timeout de su cliente de auth (gotrue) a través de create_client()/ClientOptions:
# ClientOptions solo permite fijar postgrest_client_timeout / storage_client_timeout /
# function_client_timeout, pero _init_supabase_auth_client() en
# supabase/_sync/client.py NO reenvía ninguno de esos valores al construir el cliente
# de auth. Sin un http_client explícito, gotrue arma el suyo propio
# (gotrue/_sync/gotrue_base_api.py: SyncClient(verify=..., follow_redirects=True,
# http2=True)) sin pasar `timeout`, así que hereda el default de httpx: 5 segundos.
# Ese es justo el timeout que se disparó en la verificación en vivo (login real de
# Supabase, ida y vuelta de red) y devolvió un 401 INVALID_TOKEN falso.
#
# Para controlar el timeout de verdad, esta función llama directo al endpoint REST
# de Supabase Auth (GET /auth/v1/user) en vez de pasar por el SDK. 10s, mismo orden
# de magnitud que el timeout de 8s ya usado en PriceObserver (agora_v2.py) para el
# scraping en vivo de MercadoLibre, con algo más de margen porque este chequeo corre
# en el camino crítico de CADA request de sesión web a /pulse (no es un best-effort
# en segundo plano con degradación ya prevista como el observer).
SUPABASE_AUTH_VERIFY_TIMEOUT_SECONDS = 10.0


def get_current_claims_web_or_app(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> dict:
    """
    Variante de get_current_claims que además acepta sesiones de Supabase (sitio web).

    - Primero intenta la vía existente (JWT propio del backend, HS256, app móvil).
      Si esa vía falla por cualquier motivo que NO sea "formato/firma no reconocidos"
      (p.ej. TOKEN_EXPIRED, INVALID_TOKEN_CLAIMS), se propaga tal cual: significa que
      el token SÍ es de este backend, solo que inválido por otra razón.
    - Si falla específicamente por no ser un JWT HS256 de este backend, se intenta
      validar como token de Supabase (ES256, emitido por supabase.auth.getSession()
      en el frontend web) contra la propia API REST de Supabase, con un timeout
      explícito (ver SUPABASE_AUTH_VERIFY_TIMEOUT_SECONDS arriba).

    Uso exclusivo de rutas web-facing que deben aceptar sesiones de Supabase además
    de las de la app móvil (hoy: GET /agora/v2/pulse). No reemplaza get_current_claims
    en ninguna otra ruta, para no alterar el comportamiento ya validado de la app móvil.
    """
    token = credentials.credentials

    try:
        return get_current_claims(credentials)
    except HTTPException as backend_jwt_error:
        if backend_jwt_error.detail != "INVALID_TOKEN":
            raise

    try:
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY")
        if not supabase_url or not supabase_anon_key:
            raise RuntimeError("Faltan las variables de entorno SUPABASE_URL o SUPABASE_ANON_KEY")

        resp = requests.get(
            f"{supabase_url}/auth/v1/user",
            headers={"apikey": supabase_anon_key, "Authorization": f"Bearer {token}"},
            timeout=SUPABASE_AUTH_VERIFY_TIMEOUT_SECONDS,
        )
        if resp.status_code != 200:
            raise ValueError(f"Supabase rechazó el token: {resp.status_code} {resp.text}")

        supa_user = resp.json()
        supa_user_id = supa_user.get("id")
        if not supa_user_id:
            raise ValueError("Supabase no devolvió un usuario para este token")
    except Exception as e:
        logger.warning(
            f"[AUTH] Token rechazado como JWT propio y como token Supabase: {type(e).__name__}: {e}"
        )
        raise HTTPException(status_code=401, detail="INVALID_TOKEN")

    return {
        "user_id": None,
        "email": supa_user.get("email"),
        "device_id": "web_app",
        "auth_source": "supabase",
        "supabase_user_id": supa_user_id,
    }


def get_current_user(
    claims: dict = Depends(get_current_claims),
    db: Session = Depends(get_db),
) -> User:
    """
    Carga usuario desde DB y valida:
    - existencia
    - activo
    - política de un dispositivo
    """
    user_id = int(claims["user_id"])
    device_id = claims.get("device_id")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail="USER_NOT_FOUND")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="USER_INACTIVE")

    if user.device_id and device_id and user.device_id != device_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DEVICE_MISMATCH",
                "action": "REQUIRE_RESET"
            }
        )

    return user


# ============================================================
# PLAN UTILITIES
# ============================================================

def require_entitlement(entitlement: str):
    """
    Dependencia para validar acceso a modelos según plan.

    Ejemplo:
        Depends(require_entitlement("run_epsilon"))
    """

    def _checker(
        claims: dict = Depends(get_current_claims),
        db: Session = Depends(get_db),
    ) -> Dict[str, object]:

        user_id = int(claims["user_id"])
        device_id = claims.get("device_id")

        sub = get_active_subscription(
            db,
            user_id=user_id,
        )

        plan_id = resolve_plan(sub, claims)

        if not plan_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "action": "UPGRADE_PLAN",
                    "message": "No tienes un plan activo o válido.",
                    "requiredEntitlement": entitlement,
                },
            )

        entitlements = get_entitlements_for_plan(plan_id)

        if entitlement not in entitlements:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "action": "UPGRADE_PLAN",
                    "message": "Tu plan no permite este modelo.",
                    "requiredEntitlement": entitlement,
                    "planId": plan_id if isinstance(plan_id, str) else None,
                },
            )

        return {
            "claims": claims,
            "subscription": sub,
            "planId": plan_id if isinstance(plan_id, str) else None,
            "entitlements": entitlements,
        }

    return _checker


# ============================================================
# BILLING POLICY
# ============================================================

def validate_billing_policy(
    sub: Subscription,
    claims: dict,
    expected_provider: str,
):
    """
    PolicyAgent centralizado para validar integridad de suscripción.
    """

    if getattr(settings, "POLICY_MODE", None) == "dev" or getattr(settings, "DEV_BYPASS_POLICIES", False):
        return

    is_test_mode = claims.get("test_mode") is True
    is_sandbox = getattr(settings, "MP_ENV", "sandbox") == "sandbox"

    if sub.user_id != int(claims.get("user_id")):
        raise HTTPException(status_code=403, detail="USER_MISMATCH")

    actual_provider = (
        str(sub.provider.value)
        if hasattr(sub.provider, "value")
        else str(sub.provider)
    )

    if actual_provider != str(expected_provider):

        logger.warning(
            f"[BILLING_POLICY] PROVIDER_MISMATCH | "
            f"user={claims.get('user_id')} "
            f"sub={sub.id} "
            f"expected={expected_provider} "
            f"actual={actual_provider}"
        )

        raise HTTPException(status_code=403, detail="PROVIDER_MISMATCH")

    if is_test_mode:
        return

    if not is_sandbox:

        if sub.status != "active":
            raise HTTPException(
                status_code=403,
                detail="PRODUCTION_REQUIRES_ACTIVE_SUBSCRIPTION",
            )

    else:

        if sub.status not in ("pending", "active"):
            raise HTTPException(
                status_code=403,
                detail="SANDBOX_REQUIRES_PENDING_OR_ACTIVE_SUBSCRIPTION",
            )


# ============================================================
# SUBSCRIPTION ACTIVATION LOGIC
# ============================================================

def activate_subscription_logic(
    db: Session,
    subscription: Subscription,
    provider: str,
    payment_ref: str,
    amount: int = 0,
    currency: str = "CLP",
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    auto_renew: bool = True,
):

    existing_payment = db.query(Payment).filter(
        Payment.external_id == payment_ref,
        Payment.status == "approved",
    ).first()

    if existing_payment:
        return subscription

    try:
        subscription.provider = PaymentProvider(provider)
    except Exception:
        subscription.provider = provider

    subscription.status = "active"
    subscription.external_ref = payment_ref
    subscription.start_date = start_date or _now_utc()
    subscription.end_date = end_date or (subscription.start_date + timedelta(days=30))
    subscription.auto_renew = auto_renew

    payment = db.query(Payment).filter(
        Payment.subscription_id == subscription.id,
        Payment.status == "created",
    ).first()

    if not payment:
        payment = Payment(
            user_id=subscription.user_id,
            subscription_id=subscription.id,
            provider=subscription.provider,
            amount=amount,
            currency=currency,
            status="created",
        )
        db.add(payment)

    payment.status = "approved"
    payment.external_id = payment_ref

    db.commit()
    db.refresh(subscription)

    return subscription