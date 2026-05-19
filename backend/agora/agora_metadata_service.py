from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
from backend.database.models.agora_metadata import AgoraMetadata

class AgoraMetadataService:
    @staticmethod
    def set(db: Session, key: str, value: str, expires_at: Optional[datetime] = None):
        try:
            meta = db.query(AgoraMetadata).filter(AgoraMetadata.key == key).first()
            if not meta:
                meta = AgoraMetadata(key=key)
                db.add(meta)
                
            meta.value = value
            meta.expires_at = expires_at
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            # No re-levantamos para no romper flujos principales de ÁGORA
            return None

    @staticmethod
    def get(db: Session, key: str) -> Optional[AgoraMetadata]:
        try:
            return db.query(AgoraMetadata).filter(AgoraMetadata.key == key).first()
        except SQLAlchemyError:
            db.rollback()
            return None
            
    @staticmethod
    def delete(db: Session, key: str):
        try:
            meta = db.query(AgoraMetadata).filter(AgoraMetadata.key == key).first()
            if meta:
                db.delete(meta)
                db.commit()
        except SQLAlchemyError:
            db.rollback()
