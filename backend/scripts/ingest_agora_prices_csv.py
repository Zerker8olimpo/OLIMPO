import argparse
import os
import sys

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.database.session import SessionLocal
from backend.agora.price_intelligence.manual_ingestion import ManualIngestionService

def main():
    parser = argparse.ArgumentParser(description="Ingesta de precios ÁGORA desde CSV.")
    parser.add_argument("--file", required=True, help="Ruta al archivo CSV")
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"Error: No se encuentra el archivo {args.file}")
        sys.exit(1)
        
    db = SessionLocal()
    try:
        service = ManualIngestionService()
        print(f"Iniciando ingesta desde: {args.file}")
        result = service.ingest_price_observations_csv(db, args.file)
        
        print("\n--- Resumen de Ingesta ---")
        print(f"Insertados: {result['inserted']}")
        print(f"Omitidos:   {result['skipped']}")
        print(f"Errores:    {result['errors']}")
        
        if result['error_details']:
            print("\nDetalles de errores/omisiones:")
            for err in result['error_details'][:10]:
                print(f"- {err}")
            if len(result['error_details']) > 10:
                print("...")
                
    finally:
        db.close()

if __name__ == "__main__":
    main()
