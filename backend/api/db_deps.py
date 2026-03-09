# backend/api/db_deps.py
from __future__ import annotations

from typing import Generator
from backend.database.session import SessionLocal


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()