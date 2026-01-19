"""
Risk Calculator
---------------
Módulo de cálculo estadístico de riesgo para el Observatorio.

Responsabilidad:
- Calcular volatilidad y riesgo implícito basado en series de inputs.
- Generar RiskSnapshot estandarizado y defendible.
- NO tomar decisiones ni ajustar modelos.

INVARIANTES:
- Stateless (puro)
- Determinístico
- Basado en estadística descriptiva estándar
"""

from typing import List, Literal
from statistics import mean, stdev
from math import isnan

from backend.observatory.contracts.risk_snapshot import RiskSnapshot


class RiskCalculator:
    """
    Calcula un RiskSnapshot estadístico basado en la volatilidad
    observada en los inputs de evaluación.
    """

    @staticmethod
    def calculate_from_series(
        *,
        account_id: str,
        values: List[float],
        observation_window: int
    ) -> RiskSnapshot:
        """
        Calcula riesgo estadístico a partir de una serie numérica.

        :param account_id: Identificador de la cuenta
        :param values: Serie de valores de entrada
        :param observation_window: Tamaño de la ventana analizada (referencia para confianza)
        """

        if not values or len(values) < 2:
            # Riesgo mínimo por falta de información suficiente para estadística
            return RiskSnapshot(
                account_id=account_id,
                risk_level="LOW",
                risk_score=0.0,
                volatility_index=0.0,
                confidence=0.0,
                observation_window=observation_window,
            )

        avg = mean(values)
        
        # Coeficiente de variación (CV) como proxy de volatilidad relativa
        if avg == 0:
            volatility = 0.0
        else:
            volatility = stdev(values) / abs(avg)

        # Normalización básica del riesgo [0, 1]
        # Asumimos que CV > 1.0 es volatilidad muy alta
        risk_score = min(max(volatility, 0.0), 1.0)

        # Clasificación de riesgo (defendible y simple)
        risk_level: Literal["LOW", "MEDIUM", "HIGH"] = "LOW"
        if risk_score >= 0.5:
            risk_level = "HIGH"
        elif risk_score >= 0.2:
            risk_level = "MEDIUM"

        # Confianza aumenta con tamaño de muestra relativo a la ventana esperada
        confidence = min(len(values) / observation_window, 1.0)

        if isnan(risk_score):
            risk_score = 0.0
            risk_level = "LOW"
            confidence = 0.0

        return RiskSnapshot(
            account_id=account_id,
            risk_level=risk_level,
            risk_score=risk_score,
            volatility_index=volatility,
            confidence=confidence,
            observation_window=observation_window,
        )