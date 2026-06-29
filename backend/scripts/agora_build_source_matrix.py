import json
import csv
import os
from typing import List, Dict, Any
from backend.agora.price_intelligence.source_classifier import SourceClassifier

def build_source_matrix_report(cfg_path: str, output_dir: str):
    """
    Genera el reporte de cobertura de fuentes para todas las familias de ÁGORA.
    """
    classifier = SourceClassifier()
    families_classification = classifier.classify_all_families(cfg_path)
    
    if not families_classification:
        print(f"No se pudieron clasificar familias desde {cfg_path}")
        return

    # Export to CSV
    os.makedirs(output_dir, exist_ok=True)
    
    report_path = os.path.join(output_dir, "agora_source_matrix.csv")
    with open(report_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=families_classification[0].keys())
        writer.writeheader()
        writer.writerows(families_classification)

    # Summary calculation
    summary = {
        "total_families": len(families_classification),
        "status_distribution": {},
        "market_coverage": {}
    }
    
    for fam in families_classification:
        status = fam["source_status"]
        summary["status_distribution"][status] = summary["status_distribution"].get(status, 0) + 1
        
        market_id = fam["market_id"]
        if market_id not in summary["market_coverage"]:
            summary["market_coverage"][market_id] = {
                "total": 0,
                "ready": 0,
                "manual": 0
            }
        
        summary["market_coverage"][market_id]["total"] += 1
        if status == "ready":
            summary["market_coverage"][market_id]["ready"] += 1
        elif status == "manual_only":
            summary["market_coverage"][market_id]["manual"] += 1

    # Save summary to JSON
    summary_path = os.path.join(output_dir, "agora_source_matrix_summary.json")
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    print(f"Reporte de matriz de fuentes generado en {report_path}")
    print(f"Resumen guardado en {summary_path}")
    print(f"Familias con fuente 'ready': {summary['status_distribution'].get('ready', 0)}")
    print(f"Familias 'manual_only': {summary['status_distribution'].get('manual_only', 0)}")

if __name__ == "__main__":
    build_source_matrix_report(
        "backend/cfg/CFG_AGORA_PRODUCT_FAMILIES.json",
        "backend/agora/reports"
    )
