import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Forzamos entorno seguro in-memory y variables antes de importar la app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("GOOGLE_PLAY_PUBLIC_KEY", "pytest_mock_key")
os.environ.setdefault("JWT_SECRET", "pytest_secret")

# Ensure all SQLAlchemy models are registered
import backend.database.models
from backend.database.base import Base
from backend.api.main import app
from backend.database.session import get_db

# Motor central SQLite in-memory para todos los tests
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """Provee una sesión de base de datos aislada e in-memory por cada test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    """Provee un TestClient con la dependencia de base de datos mockeada a in-memory."""
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()