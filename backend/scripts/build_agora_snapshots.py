import argparse
import os
import sys
from datetime import datetime, timezone
from sqlalchemy import select

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.database.session import SessionLocal
from backend.agora.price_intelligence.snapshot_builder import SnapshotBuilder
from backend.database.models.agora import AgoraPriceObservation

def main():
    parser = argparse.ArgumentParser(description="Construcción de snapshots ÁGORA.")
    parser.add_argument("--month", required=True, help="Mes en formato YYYY-MM")
    parser.add_argument("--market-id", help="Filtrar por mercado")
    parser.add_argument("--product-id", help="Filtrar por producto")
    parser.add_argument("--family-id", help="Filtrar por familia")
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        # Detectar targets si no se especificaron
        if args.family_id:
            targets = [(args.market_id, args.product_id, args.family_id)]
        else:
            # Parse month dates
            year_str, month_str = args.month.split('-')
            y, m = int(year_str), int(month_str)
            start_date = datetime(y, m, 1, tzinfo=timezone.utc)
            if m == 12:
                end_date = datetime(y + 1, 1, 1, tzinfo=timezone.utc)
            else:
                end_date = datetime(y, m + 1, 1, tzinfo=timezone.utc)
                
            stmt = select(
                AgoraPriceObservation.market_id, 
                AgoraPriceObservation.product_id, 
                AgoraPriceObservation.family_id
            ).where(
                AgoraPriceObservation.observed_at >= start_date,
                AgoraPriceObservation.observed_at < end_date
            ).distinct()
            
            results = db.execute(stmt).all()
            targets = [(r.market_id, r.product_id, r.family_id) for r in results]
            
            if args.market_id:
                targets = [t for t in targets if t[0] == args.market_id]
            if args.product_id:
                targets = [t for t in targets if t[1] == args.product_id]

        print(f"Iniciando construcción de snapshots para: {args.month}")
        print(f"Familias objetivo: {len(targets)}")
        
        builder = SnapshotBuilder()
        count = 0
        errors = 0
        
        for market, product, family in targets:
            try:
                snap = builder.build_monthly_snapshot(db, market, product, family, args.month)
                if snap:
                    print(f"- Creado/Actualizado: {family} ({snap.data_status}, size={snap.sample_size})")
                    count += 1
                else:
                    print(f"- Omitido (sin datos): {family}")
            except Exception as e:
                print(f"- ERROR en {family}: {str(e)}")
                errors += 1
                
        print("\n--- Resumen de Snapshots ---")
        print(f"Construidos: {count}")
        print(f"Errores:     {errors}")
                
    finally:
        db.close()

if __name__ == "__main__":
    main()
