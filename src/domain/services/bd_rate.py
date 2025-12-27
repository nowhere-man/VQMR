"""BD-Rate and BD-Metrics calculation (pure math, no I/O)."""
from typing import List, Optional, Tuple

import numpy as np
import scipy.interpolate


def _compute_integrals(
    x1: np.ndarray,
    y1: np.ndarray,
    x2: np.ndarray,
    y2: np.ndarray,
    piecewise: int,
) -> Tuple[Optional[float], Optional[float], float, float]:
    """Compute integrals of two curves over common interval."""
    try:
        p1 = np.polyfit(x1, y1, 3)
        p2 = np.polyfit(x2, y2, 3)
    except Exception:
        return None, None, 0, 0

    min_int = max(min(x1), min(x2))
    max_int = min(max(x1), max(x2))

    if max_int <= min_int:
        return None, None, 0, 0

    if piecewise == 0:
        p_int1 = np.polyint(p1)
        p_int2 = np.polyint(p2)
        int1 = np.polyval(p_int1, max_int) - np.polyval(p_int1, min_int)
        int2 = np.polyval(p_int2, max_int) - np.polyval(p_int2, min_int)
    else:
        lin = np.linspace(min_int, max_int, num=100, retstep=True)
        interval = lin[1]
        samples = lin[0]
        v1 = scipy.interpolate.pchip_interpolate(
            np.sort(x1), y1[np.argsort(x1)], samples
        )
        v2 = scipy.interpolate.pchip_interpolate(
            np.sort(x2), y2[np.argsort(x2)], samples
        )
        int1 = np.trapz(v1, dx=interval)
        int2 = np.trapz(v2, dx=interval)

    return int1, int2, min_int, max_int


def bd_rate(
    rate1: List[float],
    metric1: List[float],
    rate2: List[float],
    metric2: List[float],
    piecewise: int = 0,
) -> Optional[float]:
    """
    Calculate BD-Rate (Bjontegaard Delta Rate).

    Negative value means rate2 saves bitrate compared to rate1 (better).
    """
    if len(rate1) < 4 or len(rate2) < 4:
        return None

    lR1 = np.log(rate1)
    lR2 = np.log(rate2)
    m1_arr = np.array(metric1)
    m2_arr = np.array(metric2)

    int1, int2, min_int, max_int = _compute_integrals(m1_arr, lR1, m2_arr, lR2, piecewise)
    if int1 is None or int2 is None:
        return None

    avg_exp_diff = (int2 - int1) / (max_int - min_int)
    return (np.exp(avg_exp_diff) - 1) * 100


def bd_metrics(
    rate1: List[float],
    metric1: List[float],
    rate2: List[float],
    metric2: List[float],
    piecewise: int = 0,
) -> Optional[float]:
    """
    Calculate BD-Metrics (Bjontegaard Delta Metrics).

    Positive value means metric2 has better quality than metric1.
    """
    if len(rate1) < 4 or len(rate2) < 4:
        return None

    lR1 = np.log(rate1)
    lR2 = np.log(rate2)
    m1 = np.array(metric1)
    m2 = np.array(metric2)

    int1, int2, min_int, max_int = _compute_integrals(lR1, m1, lR2, m2, piecewise)
    if int1 is None or int2 is None:
        return None

    avg_diff = (int2 - int1) / (max_int - min_int)
    return avg_diff
