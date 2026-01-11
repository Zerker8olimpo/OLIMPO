import sys
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 1. Configuración de rutas
current_file = Path(__file__).resolve()
backend_dir = current_file.parent.parent  # .../backend
root_dir = backend_dir.parent             # .../OLIMPO
sys.path.append(str(root_dir))

# 2. Cargar .env
env_path = backend_dir / ".env"
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL")

def reset_device_id(email: str):
    """
    Elimina el device_id asociado a un usuario para permitirle
    iniciar sesión en un nuevo dispositivo.
    """
    if not DATABASE_URL:
        print("❌ Error: DATABASE_URL no encontrada en .env")
        return

    print(f"🔄 Conectando a DB para resetear dispositivo de: {email}")
    
    engine = create_engine(DATABASE_URL)
    
    # Usamos SQL directo para evitar dependencias de modelos en scripts de mantenimiento simples
    query = text("UPDATE users SET device_id = NULL WHERE email = :email")
    
    with engine.connect() as conn:
        result = conn.execute(query, {"email": email})
        conn.commit()
        
        if result.rowcount > 0:
            print(f"✅ Éxito: Dispositivo desvinculado para {email}")
        else:
            print(f"⚠️ No se encontró el usuario {email} o no se requirieron cambios.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python -m backend.scripts.reset_device <email_usuario>")
    else:
        reset_device_id(sys.argv[1])