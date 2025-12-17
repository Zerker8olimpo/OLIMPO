from backend.database.engine import engine
from backend.database.base import Base
import backend.database.models

def main():
    Base.metadata.create_all(bind=engine)
    print("[BOOTSTRAP] Base de datos y tablas creadas correctamente.")

if __name__ == "__main__":
    main()