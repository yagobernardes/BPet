# bop_twin/core/ode.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Any, Optional, Sequence, Union

import numpy as np

try:
    from scipy.integrate import solve_ivp
except ImportError as e:
    raise ImportError(
        "scipy não está instalado. Instale com: pip install scipy"
    ) from e


ArrayLike = Union[Sequence[float], np.ndarray]
OdeFun = Callable[[float, np.ndarray], ArrayLike]


def integrate_ode(
    fun: OdeFun,
    y0: ArrayLike,
    t_span: tuple[float, float],
    t_eval: Optional[np.ndarray] = None,
    method: str = "RK45",
    rtol: float = 1e-6,
    atol: float = 1e-9,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Wrapper simples do solve_ivp retornando dict compatível com seus testes.

    Retorna:
      {
        "t": np.ndarray shape (N,),
        "y": np.ndarray shape (n_states, N),
        "success": bool,
        "message": str
      }
    """
    y0 = np.asarray(y0, dtype=float)

    if t_eval is None:
        # default: 1000 pontos uniformes
        t_eval = np.linspace(t_span[0], t_span[1], 1000)

    def _fun(t, y):
        dy = fun(t, y)
        return np.asarray(dy, dtype=float)

    sol = solve_ivp(
        fun=_fun,
        t_span=t_span,
        y0=y0,
        t_eval=np.asarray(t_eval, dtype=float),
        method=method,
        rtol=rtol,
        atol=atol,
    )

    if verbose:
        print(f"[integrate_ode] success={sol.success} message={sol.message}")

    return {
        "t": sol.t,
        "y": sol.y,
        "success": bool(sol.success),
        "message": str(sol.message),
    }


def run_hold_test(
    fun: OdeFun,
    p0_pa: float,
    t_hold_min: float = 5.0,
    dt_s: float = 0.5,
    pass_drop_percent: float = 1.0,
    method: str = "RK45",
) -> Dict[str, Any]:
    """
    Executa um hold test:
      - inicia em p0_pa
      - simula por t_hold_min
      - calcula ΔP% = (P0 - P_end)/P0 * 100
      - PASS se ΔP% <= pass_drop_percent

    Assumimos que a variável de pressão principal é y[0].
    """
    t_end = float(t_hold_min) * 60.0
    t_eval = np.arange(0.0, t_end + dt_s, dt_s)

    sol = integrate_ode(
        fun=fun,
        y0=[float(p0_pa)],
        t_span=(0.0, t_end),
        t_eval=t_eval,
        method=method,
        verbose=False,
    )

    p_end = float(sol["y"][0, -1])
    delta_p_percent = (float(p0_pa) - p_end) / float(p0_pa) * 100.0
    passed = delta_p_percent <= float(pass_drop_percent)

    return {
        "t": sol["t"],
        "p0_pa": float(p0_pa),
        "p_end_pa": p_end,
        "delta_p_percent": float(delta_p_percent),
        "pass": bool(passed),
        "pass_drop_percent": float(pass_drop_percent),
        "success": sol["success"],
        "message": sol["message"],
    }