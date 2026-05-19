import os
import sys

# Agregar el directorio raíz al path para poder importar backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy import inspect
from backend.database.engine import engine
from backend.database.base import Base
from backend.database.models.agora_metadata import AgoraMetadata

def create_agora_metadata_table():
    """
    Script idempotente para crear la tabla agora_metadata si no existe.
    """
    inspector = inspect(engine)
    if "agora_metadata" not in inspector.get_table_names():
        AgoraMetadata.__table__.create(bind=engine)
        
    print("agora_metadata table ready")

if __name__ == "__main__":
    create_agora_metadata_table()
