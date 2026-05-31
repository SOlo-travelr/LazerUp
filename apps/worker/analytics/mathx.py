"""Pure-Python statistics helpers for the scoring engines.

No numpy dependency — keeps the worker image small and the math auditable.
Every function is deterministic and side-effect free.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def acceleration(recent: float, prior: float, eps: float = 1.0) -> float:
    """Normalized growth of ``recent`` vs ``prior`` window.

    ``eps`` tames explosive ratios on tiny bases (docs/ALGORITHMS.md §1).
    """
    return (recent - prior) / (prior + eps)


def log_damp(a: float) -> float:
    """Signed log damping: sign(a) * ln(1 + |a|)."""
    return math.copysign(math.log1p(abs(a)), a)


def sigmoid(x: float) -> float:
    """Logistic squash to (0, 1), overflow-safe."""
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def stdev(values: Sequence[float]) -> float:
    """Population standard deviation."""
    n = len(values)
    if n < 2:
        return 0.0
    mu = mean(values)
    var = sum((v - mu) ** 2 for v in values) / n
    return math.sqrt(var)


def zscores(values: Sequence[float]) -> list[float]:
    """Z-score each value across the population. Zeros when no spread."""
    sd = stdev(values)
    if sd == 0.0:
        return [0.0 for _ in values]
    mu = mean(values)
    return [(v - mu) / sd for v in values]


def minmax(values: Sequence[float]) -> list[float]:
    """Scale to [0, 1]. Returns 0.5 for every element when all are equal."""
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.5 for _ in values]
    span = hi - lo
    return [(v - lo) / span for v in values]


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))
