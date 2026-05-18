import os
import sys

# Agregar el directorio raíz al path para poder importar backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy import inspect
from backend.database.engine import engine
from backend.database.base import Base
from backend.database.models.agora import AgoraPriceObservation, AgoraFamilyMonthlySnapshot

def create_agora_tables():
    """
    Script idempotente para crear las tablas de ÁGORA si no existen.
    """
    print("--- Verificando tablas de ÁGORA ---")
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    tables_to_create = []
    if "agora_price_observations" not in existing_tables:
        tables_to_create.append(AgoraPriceObservation.__table__)
        print("- Programando creación de: agora_price_observations")
    else:
        print("- Ya existe: agora_price_observations")
        
    if "agora_family_monthly_snapshots" not in existing_tables:
        tables_to_create.append(AgoraFamilyMonthlySnapshot.__table__)
        print("- Programando creación de: agora_family_monthly_snapshots")
    else:
        print("- Ya existe: agora_family_monthly_snapshots")
        
    if tables_to_create:
        print("\nCreando tablas...")
        Base.metadata.create_all(bind=engine, tables=tables_to_create)
        print("¡Tablas creadas exitosamente!")
    else:
        print("\nNo se requiere ninguna acción.")
    
    print("--- Fin del proceso ---")

if __name__ == "__main__":
    create_agora_tables()
