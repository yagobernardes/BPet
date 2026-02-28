from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal, Dict, Any, Tuple
import numpy as np

TestMode = Literal["low", "high"]
PressureUnit = Literal["psi", "pa", "bar"]


@dataclass(frozen=True)
class PressureTestSpec:
    mode: TestMode
    observation_min: float = 5.0

    # Low test constraints
    low_min_psi: float = 250.0
    low_max_psi: float = 350.0
    low_drain_upper_psi: float = 500.0  # if between 350 and 500, must drain before observing
    low_max_rise_psi: float = 10.0      # max allowed rise during observation (note in Anexo A)

    # Stability limits (Tabela 1 - Anexo A)
    max_drop_low_psi: float = 10.0
    max_drop_high_psi: float = 40.0

    # PE-1PBR-00051 item 3.1.4 I
    min_high_test_psi: float = 2000.0
    enforce_min_high_test: bool = True

    # PE-1PBR-00051 item 3.g / Anexo A 3.f
    require_rwp_stabilization_rule: bool = False
    min_rwp_fraction: float = 0.97

    # N-2752 / N-2753: Pmedida no BOP = Pteste + 0.1704 * rho_rel * LDA
    check_measured_bop_pressure: bool = False
    measured_bop_constant_psi_per_m_sg: float = 0.1704


@dataclass(frozen=True)
class PressureTestResult:
    ok: bool
    reason: str
    details: Dict[str, Any]


def _as_np(a) -> np.ndarray:
    x = np.asarray(a, dtype=float)
    if x.ndim != 1:
        raise ValueError("time and pressure must be 1D sequences")
    return x


def _to_psi(pressure: np.ndarray, pressure_unit: PressureUnit) -> np.ndarray:
    unit = str(pressure_unit).lower()
    if unit == "psi":
        return pressure
    if unit == "pa":
        return pressure / 6894.75729
    if unit == "bar":
        return pressure * 14.5037738
    raise ValueError(f"Unsupported pressure unit: {pressure_unit}")


def _rolling_median(x: np.ndarray, window: int) -> np.ndarray:
    """
    Robust smoothing to ignore spikes (vale/pico). Window is odd recommended.
    No scipy dependency.
    """
    if window <= 1:
        return x.copy()
    w = int(window)
    if w % 2 == 0:
        w += 1
    pad = w // 2
    xp = np.pad(x, (pad, pad), mode="edge")
    out = np.empty_like(x)
    for i in range(len(x)):
        out[i] = np.median(xp[i:i + w])
    return out


def _window_indices(t: np.ndarray, t_end: float, duration_s: float) -> np.ndarray:
    t0 = t_end - duration_s
    return np.where((t >= t0) & (t <= t_end))[0]


def _robust_start_end_mean(t: np.ndarray, p: np.ndarray, idx: np.ndarray) -> Tuple[float, float]:
    """
    Compute robust start/end pressure for the observation window:
    average over first 20% and last 20% of points to avoid endpoint noise.
    """
    n = len(idx)
    if n < 10:
        raise ValueError("Not enough samples inside observation window")
    k = max(3, int(0.2 * n))
    i0 = idx[:k]
    i1 = idx[-k:]
    return float(np.mean(p[i0])), float(np.mean(p[i1]))


def _max_overpressure_allowed(rwp_psi: float) -> float:
    # Anexo A: max above RWP = min(5% of RWP, 500 psi)
    return min(0.05 * rwp_psi, 500.0)


def _bop_measured_pressure_psi(
    ptest_psi: float,
    fluid_density_kg_m3: float,
    lda_m: float,
    constant_psi_per_m_sg: float,
) -> float:
    # rho_rel ~ specific gravity (1.0 ~= 1000 kg/m3)
    rho_rel = float(fluid_density_kg_m3) / 1000.0
    hydro_component = float(constant_psi_per_m_sg) * rho_rel * float(lda_m)
    return float(ptest_psi) + hydro_component


def evaluate_pressure_test(
    time_s,
    pressure_psi,
    spec: PressureTestSpec,
    *,
    designated_pressure_psi: Optional[float] = None,
    rwp_psi: Optional[float] = None,
    pressure_unit: PressureUnit = "psi",
    smooth_window: int = 11,
    high_test_justified_below_min: bool = False,
    bop_nominal_pressure_psi: Optional[float] = None,
    fluid_density_kg_m3: Optional[float] = None,
    lda_m: Optional[float] = None,
) -> PressureTestResult:
    """
    Implements Petrobras Anexo A acceptance logic:
    - Stable behavior measured in last observation window (default 5 min)
      using robust smoothing (median) and robust start/end means.
    - Low pressure must remain between 250 and 350 psi during observation.
      If initial observation begins above 350, must drain before observing.
      If exceeded 500 during pressurization -> stop, drain to zero, redo.
    - High pressure must remain above designated pressure during observation;
      if it falls below, repressurize and restart the observation window.
    - Optional RWP overpressure check: cannot exceed RWP + min(5%RWP, 500 psi).
    """
    t = _as_np(time_s)
    p_raw_in = _as_np(pressure_psi)
    if len(t) != len(p_raw_in):
        raise ValueError("time_s and pressure_psi must have same length")
    if len(t) < 20:
        return PressureTestResult(False, "series_too_short", {"n": len(t)})

    # Sort by time if needed
    if np.any(np.diff(t) < 0):
        order = np.argsort(t)
        t = t[order]
        p_raw_in = p_raw_in[order]

    # Internal calculations in psi (keeps Petrobras criteria directly in psi)
    p_raw = _to_psi(p_raw_in, pressure_unit)

    # Smooth to ignore spikes (vale/pico) as recommended by Anexo A
    p = _rolling_median(p_raw, smooth_window)

    obs_s = spec.observation_min * 60.0
    t_end = float(t[-1])
    idx = _window_indices(t, t_end, obs_s)
    if len(idx) < 10:
        return PressureTestResult(False, "insufficient_samples_in_observation_window",
                                  {"observation_s": obs_s, "n_obs": len(idx)})

    p_start, p_end = _robust_start_end_mean(t, p, idx)
    drop = p_start - p_end  # positive drop means pressure decreased
    rise = p_end - p_start  # positive rise means pressure increased

    # N-2752 / N-2753 optional depth-corrected check
    if (
        spec.check_measured_bop_pressure
        and bop_nominal_pressure_psi is not None
        and fluid_density_kg_m3 is not None
        and lda_m is not None
    ):
        ptest_psi = float(np.max(p))
        p_bop_measured_psi = _bop_measured_pressure_psi(
            ptest_psi=ptest_psi,
            fluid_density_kg_m3=float(fluid_density_kg_m3),
            lda_m=float(lda_m),
            constant_psi_per_m_sg=float(spec.measured_bop_constant_psi_per_m_sg),
        )
        if p_bop_measured_psi > float(bop_nominal_pressure_psi):
            return PressureTestResult(
                False,
                "bop_measured_pressure_above_nominal_limit",
                {
                    "ptest_surface_psi": ptest_psi,
                    "p_measured_bop_psi": p_bop_measured_psi,
                    "bop_nominal_psi": float(bop_nominal_pressure_psi),
                    "fluid_density_kg_m3": float(fluid_density_kg_m3),
                    "lda_m": float(lda_m),
                    "formula_constant_psi_per_m_sg": float(spec.measured_bop_constant_psi_per_m_sg),
                },
            )

    # Optional overpressure constraint (Anexo A)
    if rwp_psi is not None:
        pmax = float(np.max(p))
        allowed = rwp_psi + _max_overpressure_allowed(rwp_psi)
        if pmax > allowed:
            return PressureTestResult(
                False,
                "overpressure_above_rwp_limit",
                {"pmax": pmax, "rwp": rwp_psi, "allowed_max": allowed},
            )

    # Mode-specific checks
    if spec.mode == "low":
        # Check if any value in observation window is outside 250..350
        p_obs = p[idx]
        pmin_obs = float(np.min(p_obs))
        pmax_obs = float(np.max(p_obs))

        # Hard rule: must stay 250..350 throughout observation
        if pmin_obs < spec.low_min_psi or pmax_obs > spec.low_max_psi:
            # Additional rule: if pressurization exceeded 500 psi -> must drain to zero and redo
            # We can only infer from data if ever exceeded 500 prior to the window end.
            ever_above_500 = bool(np.any(p > spec.low_drain_upper_psi))
            if ever_above_500:
                return PressureTestResult(
                    False,
                    "low_test_exceeded_500psi_requires_redo",
                    {"pmin_obs": pmin_obs, "pmax_obs": pmax_obs, "limit_upper": spec.low_drain_upper_psi},
                )
            return PressureTestResult(
                False,
                "low_test_outside_250_350_during_observation",
                {"pmin_obs": pmin_obs, "pmax_obs": pmax_obs, "range": (spec.low_min_psi, spec.low_max_psi)},
            )

        # Stability: max allowed drop is 10 psi (Tabela 1)
        if drop > spec.max_drop_low_psi:
            return PressureTestResult(
                False,
                "low_test_drop_exceeds_limit",
                {"drop": drop, "limit_drop": spec.max_drop_low_psi, "p_start": p_start, "p_end": p_end},
            )

        # Low test additional note: max rise in observation window is 10 psi
        if rise > spec.low_max_rise_psi:
            return PressureTestResult(
                False,
                "low_test_rise_exceeds_limit",
                {"rise": rise, "limit_rise": spec.low_max_rise_psi, "p_start": p_start, "p_end": p_end},
            )

        return PressureTestResult(True, "ok", {"p_start": p_start, "p_end": p_end, "drop": drop, "rise": rise})

    if spec.mode == "high":
        if designated_pressure_psi is None:
            return PressureTestResult(False, "missing_designated_pressure_for_high_test", {})

        if (
            spec.enforce_min_high_test
            and float(designated_pressure_psi) < float(spec.min_high_test_psi)
            and not bool(high_test_justified_below_min)
        ):
            return PressureTestResult(
                False,
                "high_test_designated_pressure_below_minimum_2000psi",
                {
                    "designated": float(designated_pressure_psi),
                    "minimum_required": float(spec.min_high_test_psi),
                    "high_test_justified_below_min": bool(high_test_justified_below_min),
                },
            )

        p_obs = p[idx]
        pmin_obs = float(np.min(p_obs))
        if pmin_obs < float(designated_pressure_psi):
            return PressureTestResult(
                False,
                "high_test_below_designated_requires_repressurize_restart_window",
                {"pmin_obs": pmin_obs, "designated": float(designated_pressure_psi)},
            )

        # Stability: max allowed drop is 40 psi (Tabela 1)
        if drop > spec.max_drop_high_psi:
            return PressureTestResult(
                False,
                "high_test_drop_exceeds_limit",
                {"drop": drop, "limit_drop": spec.max_drop_high_psi, "p_start": p_start, "p_end": p_end},
            )

        if spec.require_rwp_stabilization_rule and rwp_psi is not None:
            stabilization_limit = max(
                float(designated_pressure_psi),
                float(spec.min_rwp_fraction) * float(rwp_psi),
            )
            if p_end < stabilization_limit:
                return PressureTestResult(
                    False,
                    "high_test_stabilization_below_required_limit",
                    {
                        "p_end": p_end,
                        "stabilization_limit": stabilization_limit,
                        "designated": float(designated_pressure_psi),
                        "rwp": float(rwp_psi),
                        "min_rwp_fraction": float(spec.min_rwp_fraction),
                    },
                )

        return PressureTestResult(True, "ok", {"p_start": p_start, "p_end": p_end, "drop": drop})

    return PressureTestResult(False, "unknown_mode", {"mode": spec.mode})
