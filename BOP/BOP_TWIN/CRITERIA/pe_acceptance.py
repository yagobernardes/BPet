from __future__ import annotations
import numpy as np

def drop_percent(p0: float, p_end: float) -> float:
    return (p0 - p_end) / p0 * 100.0

def acceptance_hold_drop(t: np.ndarray, p: np.ndarray, window_s: float = 300.0, max_drop_percent: float = 1.0) -> dict:
    """
    Regra genérica: em uma janela final de hold, a queda percentual não pode exceder max_drop_percent.
    """
    t = np.asarray(t, dtype=float)
    p = np.asarray(p, dtype=float)
    t_end = t[-1]
    mask = t >= (t_end - window_s)
    if not np.any(mask):
        mask = slice(None)

    p0 = float(p[mask][0])
    pend = float(p[mask][-1])
    dp = drop_percent(p0, pend)
    return {"delta_p_percent": float(dp), "pass": bool(dp <= max_drop_percent)}