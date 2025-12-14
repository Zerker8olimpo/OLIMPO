"""
Normalizers
-----------

Normalización defensiva de valores a [0,1] y utilidades simples
para preparar los drivers y inputs observacionales
"""

from typing import Dict


def clip01(x: float) -> float:
    if x is None:
        return 0.0
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)


def normalize_minmax(value: float, vmin: float, vmax: float) -> float:
    """
    Normaliza a [0,1] por min-max. Defensivo.
    """
    if vmax <= vmin:
        return 0.0
    x = (value - vmin) / (vmax - vmin)
    return clip01(x)


def normalize_drivers(drivers: Dict[str, float]) -> Dict[str, float]:
    """
    Asegura que todos los drivers estén en [0,1].
    """
    return {k: clip01(v) for k, v in (drivers or {}).items()}
