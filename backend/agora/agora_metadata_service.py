from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from backend.database.models.agora_metadata import AgoraMetadata

class AgoraMetadataService:
    @staticmethod
    def set(db: Session, key: str, value: str, expires_at: Optional[datetime] = None):
        meta = db.query(AgoraMetadata).filter(AgoraMetadata.key == key).first()
        if not meta:
            meta = AgoraMetadata(key=key)
            db.add(meta)
            
        meta.value = value
        meta.updated_at = datetime.now(timezone.utc)
        meta.expires_at = expires_at
        db.commit()

    @staticmethod
    def get(db: Session, key: str) -> Optional[AgoraMetadata]:
        return db.query(AgoraMetadata).filter(AgoraMetadata.key == key).first()
