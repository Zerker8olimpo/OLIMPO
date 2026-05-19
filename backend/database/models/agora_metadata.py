from sqlalchemy import Column, String, Integer, DateTime
from backend.database.base import Base

class AgoraMetadata(Base):
    """
    Tabla persistente para configuraciones y tokens dinámicos de ÁGORA.
    Evita depender de variables de entorno para datos que cambian frecuentemente (como OAuth tokens).
    """
    __tablename__ = "agora_metadata"
    
    key: str = Column(String(255), primary_key=True)
    value: str = Column(String, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
