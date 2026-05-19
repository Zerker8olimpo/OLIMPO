import os
import csv

def create_template():
    template_dir = os.path.join("backend", "agora", "templates")
    os.makedirs(template_dir, exist_ok=True)
    
    template_path = os.path.join(template_dir, "agora_historical_prices_template.csv")
    
    headers = [
        "market_id", "product_id", "family_id", "source_id", 
        "raw_product_name", "price", "currency", "unit", 
        "quantity", "observed_at", "confidence", "source_name"
    ]
    
    sample_rows = [
        {
            "market_id": "chile_construccion",
            "product_id": "tubos_pvc_sanitario",
            "family_id": "pvc_sanitario_110mm",
            "source_id": "meli",
            "raw_product_name": "Tubo PVC Sanitario 110mm x 3m",
            "price": "12500",
            "currency": "CLP",
            "unit": "unidad",
            "quantity": "1",
            "observed_at": "2026-01-15",
            "confidence": "1.0",
            "source_name": "Mercado Libre"
        }
    ]
    
    with open(template_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(sample_rows)
        
    print(f"Template created at: {template_path}")

if __name__ == "__main__":
    create_template()
