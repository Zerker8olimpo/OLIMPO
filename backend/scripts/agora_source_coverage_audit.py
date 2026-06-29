import json
import csv
import os
from typing import List, Dict, Any

def audit_agora_universe(cfg_path: str, output_dir: str):
    """
    Audita el universo de ÁGORA desde el archivo de configuración canónico.
    Genera reportes CSV de mercados, productos y familias.
    """
    if not os.path.exists(cfg_path):
        print(f"Error: {cfg_path} no encontrado.")
        return

    with open(cfg_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    products_data = cfg.get("products", [])
    
    families_report = []
    markets_summary = {}
    products_summary = []

    for product in products_data:
        market_id = product.get("market_id")
        market_nombre = product.get("market_nombre")
        product_id = product.get("product_id")
        product_nombre = product.get("product_nombre")
        observation_priority = product.get("observation_priority")
        contamination_risk = product.get("price_contamination_risk")
        dominant_units = product.get("dominant_units", [])

        # Mercado summary
        if market_id not in markets_summary:
            markets_summary[market_id] = {
                "market_id": market_id,
                "market_nombre": market_nombre,
                "products_count": 0,
                "families_count": 0
            }
        markets_summary[market_id]["products_count"] += 1

        # Producto summary
        families = product.get("families", [])
        products_summary.append({
            "market_id": market_id,
            "product_id": product_id,
            "product_nombre": product_nombre,
            "families_count": len(families),
            "observation_priority": observation_priority,
            "contamination_risk": contamination_risk
        })
        markets_summary[market_id]["families_count"] += len(families)

        # Familia detail
        for family in families:
            family_id = family.get("family_id")
            family_nombre = family.get("family_nombre")
            obs_unit = family.get("observation_unit", [])
            profile = family.get("price_observation_profile", {})
            strategy = profile.get("source_strategy", {})
            conf_rules = profile.get("confidence_rules", {})

            families_report.append({
                "market_id": market_id,
                "product_id": product_id,
                "family_id": family_id,
                "family_nombre": family_nombre,
                "observation_unit": "|".join(obs_unit),
                "primary_source_type": strategy.get("primary_source_type"),
                "min_sample_size": conf_rules.get("min_sample_size"),
                "min_similarity_score": conf_rules.get("min_similarity_score"),
                "contamination_risk": contamination_risk,
                "observation_priority": observation_priority
            })

    # Export to CSV
    os.makedirs(output_dir, exist_ok=True)

    # 1. Family Universe
    with open(os.path.join(output_dir, "agora_family_universe.csv"), 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=families_report[0].keys()) if families_report else None
        if writer:
            writer.writeheader()
            writer.writerows(families_report)

    # 2. Market Summary
    with open(os.path.join(output_dir, "agora_market_summary.csv"), 'w', encoding='utf-8', newline='') as f:
        if markets_summary:
            writer = csv.DictWriter(f, fieldnames=list(markets_summary.values())[0].keys())
            writer.writeheader()
            writer.writerows(markets_summary.values())

    # 3. Product Summary
    with open(os.path.join(output_dir, "agora_product_summary.csv"), 'w', encoding='utf-8', newline='') as f:
        if products_summary:
            writer = csv.DictWriter(f, fieldnames=products_summary[0].keys())
            writer.writeheader()
            writer.writerows(products_summary)

    print(f"Reportes generados en {output_dir}")
    print(f"Total Mercados: {len(markets_summary)}")
    print(f"Total Productos: {len(products_summary)}")
    print(f"Total Familias: {len(families_report)}")

if __name__ == "__main__":
    audit_agora_universe(
        "backend/cfg/CFG_AGORA_PRODUCT_FAMILIES.json",
        "backend/agora/reports"
    )
