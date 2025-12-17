from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "OLIMPO"
    APP_ENV: str = "development"
    APP_VERSION: str = "0.0.0"
    DATABASE_URL: str = "sqlite:///backend/db/olimpo.db"
    CORS_ORIGINS: str = "*"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()