import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

# 1. Determinar la ruta del archivo .env (Unificación)
# parents[2] desde backend/core/settings.py apunta a la raíz del proyecto (OLIMPO)
BASE_DIR = Path(__file__).resolve().parents[2]
env_path = BASE_DIR / ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(env_path) if env_path.exists() else None,
        env_file_encoding='utf-8',
        extra='ignore'
    )

    # App
    APP_NAME: str = "OLIMPO"
    APP_ENV: str = "development"
    APP_VERSION: str = "1.0.0"
    DATABASE_URL: str = "sqlite:///backend/db/olimpo.db"
    CORS_ORIGINS: str = "*"
    APP_CHANNEL: str = "playstore"

    # Payments Authority Layer (PAL)
    PAYMENTS_MODE: str = "local"
    POLICY_MODE: str = "strict"
    DEV_BYPASS_POLICIES: bool = False
    DEV_ONLY: bool = False

    # Security
    JWT_SECRET: Optional[str] = None
    SECRET_KEY: Optional[str] = None

    # Google
    GOOGLE_OAUTH_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    # Google Play Billing
    GOOGLE_PLAY_VERIFY_ENABLED: bool = False
    GOOGLE_PLAY_MODE: str = "sandbox"

    # Google Play Billing (Real)
    GOOGLE_PLAY_PACKAGE_NAME: str = "com.tuapp.olimpo"
    GOOGLE_PLAY_SERVICE_ACCOUNT_JSON: str = ""

    # Mercado Pago
    MERCADOPAGO_MODE: str = "sandbox"
    ALLOW_MP_IN_APP: bool = False
    ALLOW_MP_CHECKOUT: bool = True
    MP_WEBHOOK_ENABLED: bool = True

    # Mercado Pago Keys
    MP_ACCESS_TOKEN: str = ""
    MP_ACCESS_TOKEN_SANDBOX: Optional[str] = None
    MP_PUBLIC_KEY: Optional[str] = None
    MP_TEST_PAYER_EMAIL: Optional[str] = None
    MP_WEBHOOK_SECRET: str = ""

    # Webhooks / URLs
    PUBLIC_BASE_URL: str = "https://olimpo-backend.onrender.com"
    API_BASE_URL: str = "http://localhost:8000"
    ENTERPRISE_PORTAL_URL: str = "https://olimpo.app/empresas"

    # ÁGORA Capture Pipeline
    AGORA_CAPTURE_ENABLED: bool = False
    AGORA_CAPTURE_SOURCE: str = "manual_seed" # manual_seed, mercado_libre_mlc
    AGORA_CAPTURE_DRY_RUN: bool = True

    @staticmethod
    def validate():
        pass

settings = Settings()