from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # === App ===
    APP_NAME: str = "OLIMPO Backend"
    ENV: str = "development"

    # === Security ===
    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # === Database ===
    DATABASE_URL: str = "sqlite:///./olimpo.db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Instancia única global (ESTO ES LO QUE FALTABA)
settings = Settings()
