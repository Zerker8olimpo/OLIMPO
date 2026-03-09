import os

# Ensure all SQLAlchemy models are registered
import backend.database.models

# Variables necesarias para tests del backend
os.environ.setdefault("GOOGLE_PLAY_PUBLIC_KEY", "pytest_mock_key")
os.environ.setdefault("JWT_SECRET", "pytest_secret")