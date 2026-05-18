from pydantic import BaseModel
from typing import Optional, List

class AgoraPriceSource(BaseModel):
    source_id: str
    source_name: str
    source_type: str  # manual, api, web, csv
    market_id: str
    product_id: Optional[str] = None
    family_id: Optional[str] = None
    enabled: bool = True
    priority: int = 1

class SourceRegistry:
    def __init__(self):
        self.sources: List[AgoraPriceSource] = [
            # Configuración por defecto: fuente CSV manual
            AgoraPriceSource(
                source_id="manual_csv_ingestion",
                source_name="Carga Manual CSV",
                source_type="csv",
                market_id="*",
                enabled=True,
                priority=10
            )
        ]

    def get_sources_for_family(self, market_id: str, product_id: str, family_id: str) -> List[AgoraPriceSource]:
        # En el futuro se puede filtrar
        return [s for s in self.sources if s.enabled]
