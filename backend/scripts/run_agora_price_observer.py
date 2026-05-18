import argparse
import os
import sys
import asyncio
from typing import Optional

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.database.session import SessionLocal
from backend.agora.price_intelligence.price_observer import PriceObserver
from backend.agora.family_catalog_service import FamilyCatalogService

async def run_observer():
    parser = argparse.ArgumentParser(description="Observador de precios ÁGORA.")
    parser.add_argument("--market-id", help="ID del mercado")
    parser.add_argument("--product-id", help="ID del producto")
    parser.add_argument("--family-id", help="ID de la familia")
    parser.add_argument("--source", default="mercado_libre_mlc", help="Fuente (default: mercado_libre_mlc)")
    parser.add_argument("--build-snapshot", action="store_true", help="Construir snapshot tras observar")
    parser.add_argument("--limit-families", type=int, default=1, help="Límite de familias si se observa mercado")
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        observer = PriceObserver()
        catalog = FamilyCatalogService()
        
        if args.family_id and args.market_id and args.product_id:
            print(f"Observando familia: {args.family_id}")
            result = await observer.observe_family_prices(
                db, args.market_id, args.product_id, args.family_id,
                source_id=args.source, build_snapshot=args.build_snapshot
            )
            print("\n--- Resultado ---")
            for k, v in result.items():
                print(f"{k}: {v}")
                
        elif args.market_id:
            c_market = catalog.resolve_market_id(args.market_id)
            print(f"Observando mercado: {c_market} (limit={args.limit_families})")
            products = catalog.list_products_by_market(c_market)
            
            total = 0
            for p in products:
                if total >= args.limit_families: break
                families = catalog.list_families_by_product(c_market, p["product_id"])
                for f in families:
                    if total >= args.limit_families: break
                    print(f"[{total+1}/{args.limit_families}] Observando {f['family_id']}...")
                    res = await observer.observe_family_prices(
                        db, c_market, p["product_id"], f["family_id"],
                        source_id=args.source, build_snapshot=args.build_snapshot
                    )
                    print(f"  -> Insertados: {res.get('inserted', 0)}, Status: {res.get('data_status')}")
                    total += 1
                    await asyncio.sleep(1.0)
            print(f"\nProceso finalizado. Total familias: {total}")
        else:
            print("Error: Debe especificar --family-id o --market-id")
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_observer())
