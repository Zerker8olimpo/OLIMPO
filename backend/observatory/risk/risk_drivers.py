"""
Risk Drivers Definitions
------------------------

Define el vocabulario formal de los drivers de riesgo utilizados por el
Observatorio Estadístico de OLIMPO.

Este módulo NO calcula riesgo. NO decide. NO interactúa con modelos core.
Su única función es describir, tipificar y documentar los drivers que el
RiskEngine puede utilizar.

INVARIANTES:
- Observacional
- Declarativo
- No decisional
- Sin dependencias del core
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class RiskDriverDefinition:
    """
    Definición formal de un driver de riesgo.
    """

    name: str
    description: str
    source: str  # input | quality | gap | shock | external
    expected_min: float = 0.0
    expected_max: float = 1.0
    unit: Optional[str] = None


class RiskDriverRegistry:
    """
    Registro central de drivers de riesgo conocidos por el Observatorio.

    Este registro actúa como:
    - catálogo auditable
    - documentación viva
    - validación semántica (opcional)
    """

    def __init__(self):
        self._drivers: Dict[str, RiskDriverDefinition] = {}
        self._register_defaults()

    # -------------------------------------------------
    # Registro
    # -------------------------------------------------

    def register(self, driver: RiskDriverDefinition) -> None:
        """
        Registra un driver de riesgo.
        Si ya existe, se sobreescribe explícitamente.
        """
        self._drivers[driver.name] = driver

    def get(self, name: str) -> Optional[RiskDriverDefinition]:
        return self._drivers.get(name)

    def all(self) -> Dict[str, RiskDriverDefinition]:
        return dict(self._drivers)

    # -------------------------------------------------
    # Defaults
    # -------------------------------------------------

    def _register_defaults(self) -> None:
        """
        Drivers base del Observatorio.
        Estos NO implican que todos se usen siempre.
        """
        defaults = [
            RiskDriverDefinition(
                name="demand_variability",
                description="Variabilidad implícita de la demanda ingresada por el usuario",
                source="input",
                unit="cv",
            ),
            RiskDriverDefinition(
                name="lead_time_uncertainty",
                description="Incertidumbre o dispersión del lead time percibido",
                source="input",
                unit="days",
            ),
            RiskDriverDefinition(
                name="market_volatility",
                description="Volatilidad percibida del mercado o precio",
                source="input",
            ),
            RiskDriverDefinition(
                name="data_quality",
                description="Penalización por calidad de entrada (inputs inválidos, outliers, inconsistencias)",
                source="quality",
            ),
            RiskDriverDefinition(
                name="helios_gap",
                description="Diferencia normalizada entre percepción del usuario y Digital Twin HELIOS",
                source="gap",
            ),
        ]

        for driver in defaults:
            self.register(driver)
