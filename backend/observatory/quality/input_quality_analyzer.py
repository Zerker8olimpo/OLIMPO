"""
Input Quality Analyzer
----------------------

Este módulo caracteriza la calidad de las entradas del usuario de forma
observacional y no invasiva. No corrige valores, no bloquea ejecución y
no interactúa con modelos core.

INVARIANTES:
- Read-only
- Side-channel
- No decisional
- Fail-open
"""

from typing import Dict, List, Tuple
from math import isfinite


class InputQualityAnalyzer:
    """
    Analiza la calidad de los inputs del usuario y devuelve flags y
    penalización cuantitativa (dq_penalty) en el rango [0,1].
    """

    def __init__(self, cfg: Dict):
        self.cfg = cfg
        self.alpha = cfg.get("alpha_invalid", 0.6)
        self.beta = cfg.get("beta_outlier", 0.25)
        self.gamma = cfg.get("gamma_inconsistency", 0.15)

    # -----------------------------
    # API pública
    # -----------------------------

    def analyze(self, inputs: Dict[str, float]) -> Dict:
        """
        Punto único de entrada.

        Retorna un diccionario compatible con InputQuality del contrato.
        Nunca lanza excepciones hacia arriba (fail-open).
        """
        try:
            invalid, missing = self._check_invalid(inputs)
            outliers = self._check_outliers(inputs)
            inconsistencies = self._check_inconsistencies(inputs)

            dq_penalty = self._compute_penalty(
                invalid=invalid,
                n_outliers=len(outliers),
                n_inconsistencies=len(inconsistencies),
            )

            return {
                "is_invalid": invalid,
                "missing_fields": missing,
                "outlier_flags": outliers,
                "inconsistency_flags": inconsistencies,
                "dq_penalty": dq_penalty,
            }

        except Exception as exc:
            # Fail-open: si algo falla, se devuelve calidad neutra
            return {
                "is_invalid": False,
                "missing_fields": [],
                "outlier_flags": [],
                "inconsistency_flags": [],
                "dq_penalty": 0.0,
            }

    # -----------------------------
    # Validaciones internas
    # -----------------------------

    def _check_invalid(self, inputs: Dict[str, float]) -> Tuple[bool, List[str]]:
        """
        Detecta valores inválidos o faltantes.
        """
        missing_fields: List[str] = []
        invalid = False

        for key, value in inputs.items():
            if value is None:
                missing_fields.append(key)
                invalid = True
                continue

            if not isfinite(value):
                invalid = True
                missing_fields.append(key)
                continue

            if value < 0:
                invalid = True

        return invalid, missing_fields

    def _check_outliers(self, inputs: Dict[str, float]) -> List[str]:
        """
        Marca outliers simples usando límites configurados.
        (No elimina valores, solo etiqueta.)
        """
        flags: List[str] = []
        limits = self.cfg.get("outlier_limits", {})

        for key, value in inputs.items():
            if key not in limits:
                continue

            lower, upper = limits[key]
            if value < lower or value > upper:
                flags.append(key)

        return flags

    def _check_inconsistencies(self, inputs: Dict[str, float]) -> List[str]:
        """
        Detecta inconsistencias lógicas simples entre campos.
        Estas reglas son heurísticas y configurables.
        """
        flags: List[str] = []
        rules = self.cfg.get("inconsistency_rules", [])

        for rule in rules:
            try:
                field = rule.get("field")
                other = rule.get("other")
                condition = rule.get("condition")

                if field in inputs and other in inputs:
                    if condition == "gt" and inputs[field] <= inputs[other]:
                        flags.append(f"{field}_le_{other}")
                    if condition == "lt" and inputs[field] >= inputs[other]:
                        flags.append(f"{field}_ge_{other}")
            except Exception:
                continue

        return flags

    # -----------------------------
    # Penalización
    # -----------------------------

    def _compute_penalty(
        self,
        invalid: bool,
        n_outliers: int,
        n_inconsistencies: int,
    ) -> float:
        """
        Calcula penalización agregada de calidad.
        """
        penalty = 0.0

        if invalid:
            penalty += self.alpha

        penalty += self.beta * n_outliers
        penalty += self.gamma * n_inconsistencies

        return min(1.0, penalty)
