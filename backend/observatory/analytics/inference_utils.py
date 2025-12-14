"""
Inference Utils
---------------

Herramientas inferenciales NO paramétricas y robustas para el Observatorio.
No hace predicción operativa. Solo describe incertidumbre y contraste.
"""

from typing import List, Tuple
from statistics import median


def iqr(values: List[float]) -> float:
    """
    IQR aproximado (robusto). Aquí simple: p75 - p25 aproximado por ordenamiento.
    """
    if not values:
        return 0.0
    xs = sorted(values)
    n = len(xs)
    q1 = xs[int(0.25 * (n - 1))]
    q3 = xs[int(0.75 * (n - 1))]
    return float(q3 - q1)


def mad(values: List[float]) -> float:
    """
    Median Absolute Deviation (robusto).
    """
    if not values:
        return 0.0
    m = median(values)
    dev = [abs(x - m) for x in values]
    return float(median(dev))


def robust_zscore(x: float, values: List[float]) -> float:
    """
    Z-score robusto usando MAD. Si MAD=0, retorna 0.
    """
    if not values:
        return 0.0
    m = median(values)
    m_ad = mad(values)
    if m_ad == 0:
        return 0.0
    return float((x - m) / (1.4826 * m_ad))


def bootstrap_ci(values: List[float], *, n_boot: int = 500, alpha: float = 0.05) -> Tuple[float, float]:
    """
    Intervalo de confianza bootstrap para la mediana.
    (Suficiente para Observatorio, no heavy ML).
    """
    if not values:
        return (0.0, 0.0)

    import random

    xs = list(values)
    meds = []
    for _ in range(n_boot):
        sample = [random.choice(xs) for _ in xs]
        meds.append(median(sample))

    meds.sort()
    lo = meds[int((alpha / 2) * (len(meds) - 1))]
    hi = meds[int((1 - alpha / 2) * (len(meds) - 1))]
    return (float(lo), float(hi))
