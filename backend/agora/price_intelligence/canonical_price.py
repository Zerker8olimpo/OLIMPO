from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any

class CanonicalPriceObservation(BaseModel):
    """
    Formato universal canónico para observaciones de precios en ÁGORA.
    Garantiza que todas las fuentes hablen el mismo idioma antes de ir a DB.
    """
    # Identidad ÁGORA
    market_id: str
    product_id: str
    family_id: str
    
    # Datos de la observación
    observed_at: datetime
    price: float
    currency: str = "CLP"
    unit: str = "unidad"
    
    # Normalización
    normalized_unit: str = "unidad"
    normalized_price: float
    price_type: str = "unit_price" # unit_price, index, tariff, transaction_price
    
    # Fuente
    source_id: str
    source_type: str # marketplace, public_catalog, admin, index
    source_name: str
    source_url: Optional[str] = None
    source_context: Dict[str, Any] = Field(default_factory=dict)
    
    # Datos crudos (trazabilidad)
    raw_product_name: str
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
    
    # Calidad
    match_score: float = 1.0
    confidence_score: float = 1.0
    is_real: bool = True
    
    # Metadatos extra
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
