import asyncio
import time
from typing import Any, Dict, List, Optional

import httpx

DEFAULT_CACHE_TTL_SECONDS = 6 * 60 * 60

# mindicador.cl expone dos tipos de series muy distintos bajo el mismo shape:
# - "nivel": dolar/uf/utm/euro/libra_cobre -> valor es un precio/índice, la
#   variación se calcula como % de cambio entre dos niveles.
# - "tasa": ipc/tpm/imacec/tasa_desempleo -> valor YA es una tasa periódica
#   (p.ej. ipc mensual en %), calcular (actual-pasado)/pasado sobre una tasa
#   no tiene sentido económico. La variación acumulada correcta es componer
#   las tasas del período: Π(1 + tasa_i/100) - 1.
RATE_STYLE_CODES = {"ipc", "tpm", "imacec", "tasa_desempleo"}


class EconomicIndicatorsClient:
    """
    Cliente para mindicador.cl (API pública del Banco Central de Chile, sin API key).
    Expone dolar, uf, utm, ipc, imacec, tpm, etc.
    """

    def __init__(self, base_url: str = "https://mindicador.cl/api", timeout: float = 10.0, cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS):
        self.base_url = base_url
        self.timeout = timeout
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _cache_get(self, codigo: str) -> Optional[Dict[str, Any]]:
        entry = self._cache.get(codigo)
        if not entry:
            return None
        if time.monotonic() - entry["cached_at"] > self.cache_ttl_seconds:
            return None
        return entry["payload"]

    def _cache_set(self, codigo: str, payload: Dict[str, Any]) -> None:
        self._cache[codigo] = {"cached_at": time.monotonic(), "payload": payload}

    @staticmethod
    def _variacion_6m(codigo: str, serie: List[Dict[str, Any]]) -> Optional[float]:
        if not serie:
            return None

        if codigo in RATE_STYLE_CODES:
            window = serie[:6]
            factor = 1.0
            has_value = False
            for point in window:
                valor = point.get("valor")
                if valor is None:
                    continue
                factor *= (1 + valor / 100.0)
                has_value = True
            return (factor - 1) if has_value else None

        if len(serie) < 2:
            return None
        valor_actual = serie[0].get("valor")
        valor_pasado = serie[min(len(serie) - 1, 5)].get("valor")
        if not valor_actual or not valor_pasado:
            return None
        try:
            return (valor_actual - valor_pasado) / valor_pasado
        except ZeroDivisionError:
            return None

    async def get_indicator(self, codigo: str) -> Dict[str, Any]:
        cached = self._cache_get(codigo)
        if cached is not None:
            return cached

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/{codigo}")
                response.raise_for_status()
                data = response.json()
        except Exception as e:
            return {"codigo": codigo, "status": "error", "valor": None, "fecha": None, "serie": [], "variacion_6m": None, "error": str(e)}

        serie = data.get("serie", [])
        valor = serie[0].get("valor") if serie else data.get("valor")
        fecha = serie[0].get("fecha") if serie else data.get("fecha")

        payload = {
            "codigo": codigo,
            "status": "ok",
            "valor": valor,
            "fecha": fecha,
            "serie": serie,
            "variacion_6m": self._variacion_6m(codigo, serie),
            "error": None,
        }
        self._cache_set(codigo, payload)
        return payload

    async def get_indicators(self, codigos: List[str]) -> Dict[str, Dict[str, Any]]:
        results = await asyncio.gather(*(self.get_indicator(codigo) for codigo in codigos))
        return {codigo: result for codigo, result in zip(codigos, results)}
