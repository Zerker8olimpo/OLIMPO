from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.api.settings import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Removed get_db from here as it is usually in api/deps.py or similar, 
# but keeping SessionLocal for imports.
# If you need get_db here for scripts:
# def get_db(): ...