from __future__ import annotations
import numpy as np

def ddt(t: np.ndarray, x: np.ndarray) -> np.ndarray:
    t = np.asarray(t, dtype=float)
    x = np.asarray(x, dtype=float)
    dx = np.gradient(x, t)
    return dx

def d2dt2(t: np.ndarray, x: np.ndarray) -> np.ndarray:
    return ddt(t, ddt(t, x))

def basic_features(t: np.ndarray, p: np.ndarray) -> dict:
    dp = ddt(t, p)
    d2p = d2dt2(t, p)
    return {
        "p_min": float(np.min(p)),
        "p_max": float(np.max(p)),
        "dp_min": float(np.min(dp)),
        "dp_max": float(np.max(dp)),
        "d2p_min": float(np.min(d2p)),
        "d2p_max": float(np.max(d2p)),
    }