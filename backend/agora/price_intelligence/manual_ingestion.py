import csv
from typing import Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from dateutil import parser

from backend.agora.price_intelligence.price_observation_service import PriceObservationService
from backend.agora.price_intelligence.price_normalizer import PriceNormalizer

class ManualIngestionService:
    def __init__(self):
        self.obs_service = PriceObservationService()
        self.normalizer = PriceNormalizer()

    def ingest_price_observations_csv(self, db: Session, csv_path: str) -> Dict[str, Any]:
        """
        Ingesta manual de precios desde un archivo CSV.
        Supports historical data with observed_at.
        """
        results = {
            "inserted": 0,
            "skipped": 0,
            "errors": 0,
            "error_details": []
        }
        
        try:
            with open(csv_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row_idx, row in enumerate(reader, start=2):
                    try:
                        market_id = row.get('market_id', '').strip()
                        product_id = row.get('product_id', '').strip()
                        family_id = row.get('family_id', '').strip()
                        source_id = row.get('source_id', row.get('source', '')).strip()
                        raw_name = row.get('raw_product_name', row.get('item_name', '')).strip()
                        price_str = row.get('price', '0').strip()
                        currency = row.get('currency', 'CLP').strip()
                        unit = row.get('unit', 'unidad').strip()
                        quantity_str = row.get('quantity', '1').strip()
                        observed_at_str = row.get('observed_at', '').strip()
                        confidence_str = row.get('confidence', '1.0').strip()
                        source_name = row.get('source_name', '').strip()
                        
                        if not all([market_id, product_id, source_id, price_str]):
                            results["skipped"] += 1
                            results["error_details"].append(f"Row {row_idx}: Missing required fields.")
                            continue
                            
                        # Validation: Price > 0
                        try:
                            price = float(price_str.replace(',', ''))
                        except ValueError:
                            results["skipped"] += 1
                            results["error_details"].append(f"Row {row_idx}: Invalid price format.")
                            continue
                            
                        if price <= 0:
                            results["skipped"] += 1
                            results["error_details"].append(f"Row {row_idx}: Price must be > 0.")
                            continue

                        # Validation: Confidence [0, 1]
                        try:
                            confidence = float(confidence_str)
                            if not (0 <= confidence <= 1):
                                confidence = 1.0
                        except ValueError:
                            confidence = 1.0
                            
                        # Validation: Rejection of fallback data
                        if source_id.lower() == "fallback":
                            results["skipped"] += 1
                            results["error_details"].append(f"Row {row_idx}: Fallback data is not accepted as real history.")
                            continue

                        if not family_id:
                            # Derivar family_id
                            matched_family, conf, reason = self.normalizer.normalize_price_item(raw_name, market_id, product_id)
                            if not matched_family:
                                results["skipped"] += 1
                                results["error_details"].append(f"Row {row_idx}: Could not match family for {raw_name}.")
                                continue
                            family_id = matched_family
                            confidence = min(confidence, conf)
                        
                        # Parse date
                        if observed_at_str:
                            try:
                                observed_at = parser.parse(observed_at_str)
                                if observed_at.tzinfo is None:
                                    observed_at = observed_at.replace(tzinfo=timezone.utc)
                            except Exception:
                                results["skipped"] += 1
                                results["error_details"].append(f"Row {row_idx}: Invalid observed_at date.")
                                continue
                        else:
                            results["skipped"] += 1
                            results["error_details"].append(f"Row {row_idx}: observed_at is mandatory for historical bootstrap.")
                            continue
                            
                        # Save
                        metadata = {
                            "source_name": source_name,
                            "quantity": quantity_str,
                            "ingested_at": datetime.now(timezone.utc).isoformat()
                        }
                        
                        obs = self.obs_service.save_price_observation(
                            db=db,
                            market_id=market_id,
                            product_id=product_id,
                            family_id=family_id,
                            source=source_id,
                            source_type="csv_historical",
                            raw_product_name=raw_name,
                            normalized_product_name=raw_name,
                            price=price,
                            currency=currency,
                            unit=unit,
                            confidence=confidence,
                            is_sample=False,
                            metadata=metadata
                        )
                        
                        if obs:
                            obs.observed_at = observed_at
                            db.commit()
                            results["inserted"] += 1
                        else:
                            results["skipped"] += 1
                            
                    except Exception as e:
                        results["errors"] += 1
                        results["error_details"].append(f"Row {row_idx} exception: {str(e)}")
                        
            return results
            
        except Exception as e:
            results["errors"] += 1
            results["error_details"].append(f"File level exception: {str(e)}")
            return results
