import os
from pathlib import Path
from dotenv import load_dotenv

# 1. Determinar la ruta del archivo .env (Unificación)
# parents[2] desde backend/core/settings.py apunta a la raíz del proyecto (OLIMPO)
BASE_DIR = Path(__file__).resolve().parents[2]
env_path = BASE_DIR / ".env"

# 2. Carga controlada y centralizada
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

class Settings:
    # App
    APP_NAME: str = os.getenv("APP_NAME", "OLIMPO")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///backend/db/olimpo.db")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")
    APP_CHANNEL: str = os.getenv("APP_CHANNEL", "playstore")

    # Payments Authority Layer (PAL)
    PAYMENTS_MODE: str = os.getenv("PAYMENTS_MODE", "local")  # local | sandbox | prod
    POLICY_MODE: str = os.getenv("POLICY_MODE", "strict")      # strict | dev
    DEV_BYPASS_POLICIES: bool = os.getenv("DEV_BYPASS_POLICIES", "false").lower() == "true"
    DEV_ONLY: bool = os.getenv("DEV_ONLY", "false").lower() == "true"

    # Security
    JWT_SECRET: str = os.getenv("JWT_SECRET")
    SECRET_KEY: str = os.getenv("SECRET_KEY")

    # Google
    GOOGLE_OAUTH_CLIENT_ID: str = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET")

    # Google Play Billing
    GOOGLE_PLAY_VERIFY_ENABLED: bool = os.getenv("GOOGLE_PLAY_VERIFY_ENABLED", "false").lower() == "true"
    GOOGLE_PLAY_MODE: str = os.getenv("GOOGLE_PLAY_MODE", "sandbox")

    # Google Play Billing (Real)
    GOOGLE_PLAY_PACKAGE_NAME: str = os.getenv("GOOGLE_PLAY_PACKAGE_NAME", "com.tuapp.olimpo")
    GOOGLE_PLAY_SERVICE_ACCOUNT_JSON: str = os.getenv("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON", "") # Ruta al archivo .json

    # Mercado Pago
    MERCADOPAGO_MODE: str = os.getenv("MERCADOPAGO_MODE", "sandbox")
    ALLOW_MP_IN_APP: bool = os.getenv("ALLOW_MP_IN_APP", "false").lower() == "true"
    ALLOW_MP_CHECKOUT: bool = os.getenv("ALLOW_MP_CHECKOUT", "true").lower() == "true"
    MP_WEBHOOK_ENABLED: bool = os.getenv("MP_WEBHOOK_ENABLED", "true").lower() == "true"

    MP_ACCESS_TOKEN: str = os.getenv("MP_ACCESS_TOKEN")
    MP_ACCESS_TOKEN_SANDBOX: str = os.getenv("MP_ACCESS_TOKEN_SANDBOX")
    MP_PUBLIC_KEY: str = os.getenv("MP_PUBLIC_KEY")
    MP_TEST_PAYER_EMAIL: str = os.getenv("MP_TEST_PAYER_EMAIL")
    MP_WEBHOOK_SECRET: str = os.getenv("MP_WEBHOOK_SECRET", "")

    # Webhooks / URLs
    PUBLIC_BASE_URL: str = os.getenv("PUBLIC_BASE_URL", "")
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")
    ENTERPRISE_PORTAL_URL: str = os.getenv("ENTERPRISE_PORTAL_URL", "https://olimpo.app/empresas")

    @staticmethod
    def validate():
        missing = []
        # Solo validamos variables críticas para el arranque
        for key in [
            "JWT_SECRET",
            "GOOGLE_OAUTH_CLIENT_ID",
            "DATABASE_URL"
        ]:
            if not os.getenv(key):
                missing.append(key)

        if missing:
            print(f"⚠️ [WARNING] Faltan variables de entorno críticas: {missing}")
            # En producción podrías lanzar un RuntimeError aquí

settings = Settings()
settings.validate()