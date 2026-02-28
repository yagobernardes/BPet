import numpy as np
from bop_twin.criteria.pressure_acceptance_v2 import PressureTestSpec, evaluate_pressure_test

def acceptance_hold_drop(
    t: np.ndarray,
    p: np.ndarray,
    window_s: float = 300.0,
    max_drop_percent: float = 1.0,
    *,
    use_petrobras_logic: bool = False,
    pressure_unit: str = "pa",
    mode: str = "high",
    designated_pressure_psi: float | None = None,
    rwp_psi: float | None = None,
) -> dict:
    """
    Mantém a assinatura antiga, mas internamente pode usar o motor novo.
    Aqui eu deixei ainda o método antigo (percentual).
    Você pode migrar por etapas: criar uma acceptance_hold_drop_v2 ao lado.
    """
    t = np.asarray(t, dtype=float)
    p = np.asarray(p, dtype=float)

    # método antigo preservado (não quebra testes existentes)
    t_end = t[-1]
    mask = t >= (t_end - window_s)
    if not np.any(mask):
        mask = slice(None)
    p0 = float(p[mask][0])
    pend = float(p[mask][-1])
    dp = (p0 - pend) / p0 * 100.0

    out = {"delta_p_percent": float(dp), "pass": bool(dp <= max_drop_percent)}

    if use_petrobras_logic:
        spec = PressureTestSpec(mode="high" if str(mode).lower() == "high" else "low")
        result = evaluate_pressure_test(
            t,
            p,
            spec,
            designated_pressure_psi=designated_pressure_psi,
            rwp_psi=rwp_psi,
            pressure_unit=pressure_unit,  # pa/psi/bar
        )
        out["petrobras"] = {
            "ok": bool(result.ok),
            "reason": result.reason,
            "details": result.details,
        }
        out["pass"] = bool(out["pass"] and result.ok)

    return out
