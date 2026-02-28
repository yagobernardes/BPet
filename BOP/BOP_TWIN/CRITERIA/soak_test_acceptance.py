from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any
import numpy as np


@dataclass(frozen=True)
class SoakTestSpec:
    duration_min: float = 15.0
    step_min: float = 5.0
    extend_if_dubious: bool = True
    dubious_fraction_of_limit: float = 0.9
    min_required_pump_interval_h: float = 4.0
    min_operation_interval_min: float = 30.0


def allowed_drop_per_step(pump_start_psi: float) -> float:
    """
    PE-1PBR-00051 item 3.1.6:
    - Pump Start 2700 psi: 6 psi ou menos a cada 5 min
    - Pump Start 4700 psi: 6 psi ou menos a cada 5 min
    - Pump Start 4600 psi: 8 psi ou menos a cada 5 min
    - Pump Start 4500 psi: 10 psi ou menos a cada 5 min
    """
    ps = int(round(pump_start_psi))
    if ps in (2700, 4700):
        return 6.0
    if ps == 4600:
        return 8.0
    if ps == 4500:
        return 10.0
    # fallback conservador: usar o mais restritivo
    return 6.0


def evaluate_soak_test(
    time_s,
    acc_pressure_psi,
    pump_start_psi: float,
    spec: SoakTestSpec = SoakTestSpec(),
    pump_stop_psi: float | None = None,
) -> Dict[str, Any]:
    """
    Checks accumulator pressure decay over 15 minutes.
    Splits into 3 blocks of 5 min and checks drop in each block.
    """
    t = np.asarray(time_s, dtype=float)
    p = np.asarray(acc_pressure_psi, dtype=float)
    if t.ndim != 1 or p.ndim != 1 or len(t) != len(p):
        raise ValueError("time_s and acc_pressure_psi must be 1D arrays with same length")

    if np.any(np.diff(t) < 0):
        order = np.argsort(t)
        t = t[order]
        p = p[order]

    dur_s = spec.duration_min * 60.0
    step_s = spec.step_min * 60.0
    t_end = float(t[-1])
    t_start = t_end - dur_s
    if t_start < float(t[0]):
        return {"ok": False, "reason": "insufficient_duration", "details": {"required_s": dur_s, "available_s": float(t[-1] - t[0])}}

    # take only last 15 minutes
    mask = (t >= t_start) & (t <= t_end)
    t15 = t[mask]
    p15 = p[mask]

    allow = allowed_drop_per_step(pump_start_psi)

    # block checks (0-5, 5-10, 10-15)
    drops = []
    for k in range(int(spec.duration_min / spec.step_min)):
        a = t_start + k * step_s
        b = a + step_s
        idx = np.where((t15 >= a) & (t15 <= b))[0]
        if len(idx) < 5:
            return {"ok": False, "reason": "insufficient_samples_in_block", "details": {"block": k, "n": int(len(idx))}}
        p0 = float(np.mean(p15[idx[:max(3, int(0.2 * len(idx)))] ]))
        p1 = float(np.mean(p15[idx[-max(3, int(0.2 * len(idx))):] ]))
        drops.append(p0 - p1)

    ok_by_block = all(d <= allow for d in drops)

    total_drop = float(np.max(p15) - np.min(p15))
    mean_drop_rate_psi_per_min = total_drop / float(spec.duration_min) if spec.duration_min > 0 else 0.0

    estimated_interval_min = None
    if pump_stop_psi is not None and mean_drop_rate_psi_per_min > 1e-12:
        pump_band = max(float(pump_stop_psi) - float(pump_start_psi), 0.0)
        estimated_interval_min = pump_band / mean_drop_rate_psi_per_min

    dubious = any(d > float(spec.dubious_fraction_of_limit) * allow for d in drops)

    if (
        ok_by_block
        and spec.extend_if_dubious
        and dubious
        and estimated_interval_min is not None
        and estimated_interval_min < float(spec.min_required_pump_interval_h) * 60.0
    ):
        return {
            "ok": False,
            "reason": "requires_extended_observation_until_pump_interval_above_4h",
            "details": {
                "drops_per_5min": drops,
                "allowed_per_5min": allow,
                "pump_start_psi": pump_start_psi,
                "pump_stop_psi": pump_stop_psi,
                "estimated_pump_interval_min": estimated_interval_min,
                "required_interval_min": float(spec.min_required_pump_interval_h) * 60.0,
                "dubious_fraction_of_limit": float(spec.dubious_fraction_of_limit),
            },
        }

    interval_below_30min = (
        estimated_interval_min is not None
        and estimated_interval_min < float(spec.min_operation_interval_min)
    )

    ok = ok_by_block

    return {
        "ok": ok,
        "reason": "ok" if ok else "drop_exceeds_limit",
        "details": {
            "drops_per_5min": drops,
            "allowed_per_5min": allow,
            "pump_start_psi": pump_start_psi,
            "pump_stop_psi": pump_stop_psi,
            "mean_drop_rate_psi_per_min": mean_drop_rate_psi_per_min,
            "estimated_pump_interval_min": estimated_interval_min,
            "interval_below_30min_risk": interval_below_30min,
        },
    }
