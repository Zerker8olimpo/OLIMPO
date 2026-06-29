from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class AgoraPriceSource(BaseModel):
    id: str
    name: str
    type: str
    authorized: bool = True
    requires_auth: bool = False
    reliability_weight: float = 0.5

class SourceRegistry:
    """
    Registro centralizado de fuentes de datos permitidas para ÁGORA.
    Evita el hardcoding de fuentes y permite gestionar permisos por mercado.
    """
    
    SOURCES = {
        "mercado_libre_mlc": {
            "name": "Mercado Libre Chile",
            "type": "marketplace",
            "authorized": True,
            "requires_auth": True,
            "reliability_weight": 0.85
        },
        "odepa_mayoristas": {
            "name": "ODEPA Mayoristas",
            "type": "public_catalog",
            "authorized": True,
            "requires_auth": False,
            "reliability_weight": 0.95
        },
        "odepa_consumidor": {
            "name": "ODEPA Consumidor",
            "type": "public_catalog",
            "authorized": True,
            "requires_auth": False,
            "reliability_weight": 0.90
        },
        "odepa_insumos": {
            "name": "ODEPA Insumos",
            "type": "public_catalog",
            "authorized": True,
            "requires_auth": False,
            "reliability_weight": 0.85
        },
        "cne_api": {
            "name": "CNE Energía API",
            "type": "public_catalog",
            "authorized": True,
            "requires_auth": True,
            "reliability_weight": 0.98
        },
        "chilecompra_api": {
            "name": "ChileCompra / Mercado Público",
            "type": "public_catalog",
            "authorized": True,
            "requires_auth": True,
            "reliability_weight": 0.95
        },
        "sernac_observatorio": {
            "name": "SERNAC Observatorio",
            "type": "public_catalog",
            "authorized": True,
            "requires_auth": False,
            "reliability_weight": 0.80
        },
        "banco_central_bde": {
            "name": "Banco Central BDE",
            "type": "index",
            "authorized": True,
            "requires_auth": True,
            "reliability_weight": 1.0
        },
        "ine_stat": {
            "name": "INE Stat / IPP",
            "type": "index",
            "authorized": True,
            "requires_auth": False,
            "reliability_weight": 0.95
        },
        "manual_seed_admin": {
            "name": "Carga Manual Admin",
            "type": "admin",
            "authorized": True,
            "requires_auth": True,
            "reliability_weight": 1.0
        },
        "supplier_csv_admin": {
            "name": "Importación Proveedor CSV",
            "type": "admin",
            "authorized": True,
            "requires_auth": True,
            "reliability_weight": 0.90
        },
        "test_source": {
            "name": "Fuente de Test",
            "type": "test",
            "authorized": True,
            "requires_auth": False,
            "reliability_weight": 1.0
        },
        "src1": {
            "name": "Fuente de Test Legacy",
            "type": "test",
            "authorized": True,
            "requires_auth": False,
            "reliability_weight": 1.0
        },
        "fallback": {
            "name": "Datos de Fallback",
            "type": "system",
            "authorized": False, # No usar para snapshots reales
            "requires_auth": False,
            "reliability_weight": 0.0
        }
    }

    @classmethod
    def is_authorized(cls, source_id: str) -> bool:
        source = cls.SOURCES.get(source_id)
        return source.get("authorized", False) if source else False

    @classmethod
    def get_source_type(cls, source_id: str) -> str:
        source = cls.SOURCES.get(source_id)
        return source.get("type", "unknown") if source else "unknown"

    @classmethod
    def get_weight(cls, source_id: str) -> float:
        source = cls.SOURCES.get(source_id)
        return source.get("reliability_weight", 0.5) if source else 0.5
