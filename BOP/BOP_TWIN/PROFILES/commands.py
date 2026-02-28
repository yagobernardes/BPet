from __future__ import annotations

def step_opening(t_step: float = 0.0, level: float = 1.0):
    def f(t: float) -> float:
        return float(level) if t >= float(t_step) else 0.0
    return f

def pulse_opening(t_on: float, t_off: float, level: float = 1.0):
    def f(t: float) -> float:
        return float(level) if (t >= t_on and t < t_off) else 0.0
    return f