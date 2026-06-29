import csv
import argparse
import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any
from backend.agora.price_intelligence.canonical_price import CanonicalPriceObservation
from backend.agora.price_intelligence.source_registry import SourceRegistry

def prepare_canonical_csv(source_id: str, input_path: str, output_path: str, market_id: str, product_id: str, family_id: str, dry_run: bool = True):
    """
    Prepara un CSV canónico ÁGORA desde una fuente cruda.
    """
    if not os.path.exists(input_path):
        print(f"Error: {input_path} no encontrado.")
        return

    # Validar fuente
    if not SourceRegistry.is_authorized(source_id):
        print(f"Error: Fuente {source_id} no autorizada.")
        return

    results = {
        "rows_read": 0,
        "rows_normalized": 0,
        "rows_rejected": 0,
        "error_details": []
    }

    canonical_rows = []

    try:
        with open(input_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row_idx, row in enumerate(reader, start=1):
                results["rows_read"] += 1
                try:
                    # TODO: Aquí se debería invocar al adaptador correspondiente
                    # Por ahora simulamos una transformación básica
                    price = float(row.get('price', 0))
                    if price <= 0:
                        results["rows_rejected"] += 1
                        continue

                    obs = CanonicalPriceObservation(
                        market_id=market_id,
                        product_id=product_id,
                        family_id=family_id,
                        observed_at=datetime.now(timezone.utc),
                        price=price,
                        normalized_price=price, # Simulación
                        source_id=source_id,
                        source_type=SourceRegistry.get_source_type(source_id),
                        source_name=SourceRegistry.SOURCES.get(source_id, {}).get("name", "Unknown"),
                        raw_product_name=row.get('raw_name', 'Unknown'),
                        source_context={"input_file": input_path, "row_index": row_idx}
                    )
                    
                    canonical_rows.append(obs.model_dump())
                    results["rows_normalized"] += 1
                except Exception as e:
                    results["rows_rejected"] += 1
                    results["error_details"].append(f"Fila {row_idx}: {str(e)}")

        if not dry_run and canonical_rows:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=canonical_rows[0].keys())
                writer.writeheader()
                writer.writerows(canonical_rows)
            print(f"Archivo canónico generado en {output_path}")

        print(f"Resumen: Leídas: {results['rows_read']}, Normalizadas: {results['rows_normalized']}, Rechazadas: {results['rows_rejected']}")
        if dry_run:
            print("MODO DRY-RUN: No se generó archivo de salida.")

    except Exception as e:
        print(f"Error procesando archivo: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepara CSV canónico ÁGORA.")
    parser.add_argument("--source", required=True, help="ID de la fuente (odepa, chilecompra, etc)")
    parser.add_argument("--input", required=True, help="Ruta al archivo de entrada crudo")
    parser.add_argument("--output", required=True, help="Ruta al archivo de salida canónico")
    parser.add_argument("--market-id", required=True)
    parser.add_argument("--product-id", required=True)
    parser.add_argument("--family-id", required=True)
    parser.add_argument("--dry-run", action="store_true", default=False)
    
    args = parser.parse_args()
    
    prepare_canonical_csv(
        args.source, args.input, args.output,
        args.market_id, args.product_id, args.family_id,
        args.dry_run
    )
