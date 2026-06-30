# backend/core/config.py
from __future__ import annotations

import os
from dataclasses import dataclass


def _env(key: str, default: str | None = None) -> str | None:
    v = os.getenv(key)
    return v if v is not None else default


@dataclass(frozen=True)
class Settings:
    APP_NAME: str = _env("APP_NAME", "OLIMPO API") or "OLIMPO API"
    APP_VERSION: str = _env("APP_VERSION", "0.1.0") or "0.1.0"
    APP_ENV: str = _env("APP_ENV", "local") or "local"

    # Auth / JWT
    GOOGLE_OAUTH_CLIENT_ID: str = _env("GOOGLE_OAUTH_CLIENT_ID", "") or ""
    JWT_SECRET: str = _env("JWT_SECRET", "") or ""

    # DB
    DATABASE_URL: str = _env("DATABASE_URL", "sqlite:///./backend/db/olimpo.db") or "sqlite:///./backend/db/olimpo.db"

    # Supabase
    SUPABASE_URL: str = _env("SUPABASE_URL", "") or ""
    SUPABASE_SERVICE_KEY: str = _env("SUPABASE_SERVICE_KEY", "") or ""

    # MercadoPago / otros (tu main.py lo usa para debug boolean)
    MP_ACCESS_TOKEN: str = _env("MP_ACCESS_TOKEN", "") or ""


settings = Settings()