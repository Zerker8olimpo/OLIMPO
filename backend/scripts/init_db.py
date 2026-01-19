import os
import sys
from sqlalchemy import create_engine
from pathlib import Path

# Agregar el directorio raíz al path para poder importar backend
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.database.base import Base
# Importamos los modelos para que Base sepa qué tablas crear
from backend.database.models.user import User
from backend.database.models.observatory_event import ObservatoryEvent
# Si tienes más modelos (Subscription, Payment), impórtalos aquí también

DATABASE_URL = "sqlite:///backend/db/olimpo.db"

def init_db():
    print(f"🚀 Iniciando inicialización de base de datos...")
    
    # Crear carpeta si no existe
    Path("backend/db").mkdir(parents=True, exist_ok=True)
    
    engine = create_engine(DATABASE_URL)
    
    print("🔨 Creando tablas basadas en los modelos actuales...")
    Base.metadata.create_all(bind=engine)
    
    print("✅ Base de datos inicializada con éxito en backend/db/olimpo.db")

if __name__ == "__main__":
    init_db()