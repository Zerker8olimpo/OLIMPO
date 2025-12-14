"""
Helios Contrast Analyzer
------------------------

Contrasta (read-only) outputs ya generados por HELIOS contra inputs/resultados observados.
Este módulo NO ejecuta HELIOS. NO modifica HELIOS. NO toca core.

Objetivo: producir un gap_score normalizado [0,1] y gap_fields.
"""

from typing import Dict, Optional, Tuple

from observatory.utils.normalizers import clip01


class HeliosContrastAnalyzer:
    def __init__(self, cfg: Optional[Dict] = None):
        self.cfg = cfg or {}
        self.threshold = float(self.cfg.get("gap_threshold", 0.75))
        self.weights = self.cfg.get("field_weights", {})  # opcional

    def compute_gap(
        self,
        *,
        user_vector: Dict[str, float],
        twin_vector: Dict[str, float],
        field_scales: Optional[Dict[str, float]] = None,
    ) -> Tuple[Optional[float], Dict[str, float]]:
        """
        user_vector: valores relevantes del usuario (o derivados post-ejecución)
        twin_vector: valores relevantes del twin (snapshot)
        field_scales: escala por campo para normalizar diferencias (ej: max esperado)
        """
        if not user_vector or not twin_vector:
            return None, {}

        fields = set(user_vector.keys()) & set(twin_vector.keys())
        if not fields:
            return None, {}

        field_scales = field_scales or {}

        gaps: Dict[str, float] = {}
        weighted_sum = 0.0
        weight_total = 0.0

        for f in fields:
            u = user_vector.get(f)
            t = twin_vector.get(f)
            if u is None or t is None:
                continue

            scale = float(field_scales.get(f, 1.0))
            if scale <= 0:
                scale = 1.0

            raw = abs(float(u) - float(t)) / scale
            g = clip01(raw)  # normaliza a [0,1]
            gaps[f] = g

            w = float(self.weights.get(f, 1.0))
            weighted_sum += g * w
            weight_total += w

        if weight_total <= 0:
            return None, gaps

        gap_score = clip01(weighted_sum / weight_total)
        return gap_score, gaps
