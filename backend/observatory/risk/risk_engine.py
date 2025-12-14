"""
Risk Engine
-----------

Motor determinístico de cálculo de riesgo implícito del Observatorio Estadístico.

Este módulo transforma inputs observados + calidad de entrada
(opcionalmente gap vs HELIOS) en un RiskSnapshot explicable.

INVARIANTES:
- Post-ejecución
- Read-only
- Determinístico (no ML)
- No-interferencia decisional
- Fail-open
"""

from typing import Dict, List, Optional

from observatory.contracts.risk_snapshot import RiskSnapshot


class RiskEngine:
    """
    Calcula riesgo implícito como metadato observacional.
    """

    def __init__(self, cfg: Dict):
        self.cfg = cfg or {}
        self.weights = self.cfg.get("weights", {})
        self.bands = self.cfg.get(
            "bands",
            {
                "LOW": 0.25,
                "MEDIUM": 0.55,
                "HIGH": 0.75,
            },
        )

    # -------------------------------------------------
    # API pública
    # -------------------------------------------------

    def compute(
        self,
        drivers: Dict[str, float],
        dq_penalty: float,
        helios_gap_score: Optional[float] = None,
    ) -> RiskSnapshot:
        """
        Punto único de cálculo de riesgo.

        :param drivers: valores normalizados [0,1] por driver
        :param dq_penalty: penalización por calidad de entrada [0,1]
        :param helios_gap_score: gap agregado vs HELIOS (opcional)
        :return: RiskSnapshot inmutable
        """

        # Ensamble de drivers efectivos (solo observación)
        effective_drivers: Dict[str, float] = dict(drivers or {})
        effective_drivers["data_quality"] = max(0.0, min(1.0, dq_penalty))

        if helios_gap_score is not None:
            effective_drivers["helios_gap"] = max(0.0, min(1.0, helios_gap_score))

        # Normalización de pesos
        weights = self._normalize_weights(effective_drivers)

        # Contribuciones por driver
        contributions: Dict[str, float] = {
            k: effective_drivers.get(k, 0.0) * weights.get(k, 0.0)
            for k in effective_drivers.keys()
        }

        # Score agregado
        risk_score: float = min(1.0, sum(contributions.values()))

        # Banda de riesgo
        risk_band: str = self._classify_band(risk_score)

        # Drivers dominantes
        top_drivers: List[str] = self._top_drivers(contributions)

        return RiskSnapshot(
            risk_score=risk_score,
            risk_band=risk_band,
            drivers=effective_drivers,
            weights=weights,
            contributions=contributions,
            top_drivers=top_drivers,
        )

    # -------------------------------------------------
    # Helpers internos
    # -------------------------------------------------

    def _normalize_weights(self, drivers: Dict[str, float]) -> Dict[str, float]:
        """
        Normaliza pesos configurados solo sobre drivers presentes.
        Si no hay pesos válidos, reparte peso uniforme.
        """
        raw_weights: Dict[str, float] = {
            k: float(self.weights.get(k, 0.0)) for k in drivers.keys()
        }

        total = sum(raw_weights.values())
        if total <= 0.0:
            n = len(raw_weights)
            if n == 0:
                return {}
            return {k: 1.0 / n for k in raw_weights.keys()}

        return {k: v / total for k, v in raw_weights.items()}

    def _classify_band(self, risk_score: float) -> str:
        """
        Clasifica el score en banda de riesgo.
        """
        if risk_score < self.bands.get("LOW", 0.25):
            return "LOW"
        if risk_score < self.bands.get("MEDIUM", 0.55):
            return "MEDIUM"
        if risk_score < self.bands.get("HIGH", 0.75):
            return "HIGH"
        return "CRITICAL"

    def _top_drivers(self, contributions: Dict[str, float], n: int = 3) -> List[str]:
        """
        Retorna los drivers con mayor contribución.
        """
        if not contributions:
            return []

        return [
            k
            for k, _ in sorted(
                contributions.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:n]
        ]
