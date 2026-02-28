from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Literal

ActuatorType = Literal["annular", "ram"]


@dataclass(frozen=True)
class FunctionTestSpec:
    max_close_annular_s: float = 60.0
    max_close_ram_s: float = 45.0
    max_close_annular_surface_small_s: float = 30.0
    max_close_annular_surface_large_s: float = 45.0
    max_close_ram_surface_s: float = 30.0
    max_subsea_kill_choke_valve_time_s: float = 45.0
    validate_regulators: bool = False
    regulator_setpoints_psi: tuple[float, ...] = (500.0, 1000.0, 1500.0, 3000.0)
    regulator_min_allowed_psi: float = 700.0
    regulator_max_allowed_psi: float = 2800.0


def _annular_limit(record: Dict[str, Any], spec: FunctionTestSpec) -> float:
    env = str(record.get("environment", "subsea")).lower()
    if env == "surface":
        bore_in = float(record.get("bore_in", 18.75))
        if bore_in >= 18.75:
            return float(spec.max_close_annular_surface_large_s)
        return float(spec.max_close_annular_surface_small_s)
    return float(spec.max_close_annular_s)


def _ram_limit(record: Dict[str, Any], spec: FunctionTestSpec) -> float:
    env = str(record.get("environment", "subsea")).lower()
    if env == "surface":
        return float(spec.max_close_ram_surface_s)
    return float(spec.max_close_ram_s)


def _evaluate_regulators(
    regulator_records: List[Dict[str, Any]],
    spec: FunctionTestSpec,
) -> Dict[str, Any]:
    if not regulator_records:
        return {"ok": True, "fails": [], "covered_setpoints_psi": []}

    fails = []
    covered = []
    setpoints = [float(x) for x in spec.regulator_setpoints_psi]
    tol_psi = 25.0

    for target in setpoints:
        if any(abs(float(r.get("setpoint_psi", -1e9)) - target) <= tol_psi for r in regulator_records):
            covered.append(target)
        else:
            fails.append(
                {
                    "type": "missing_regulator_setpoint",
                    "setpoint_psi": target,
                    "tolerance_psi": tol_psi,
                }
            )

    low_candidates = [
        float(r.get("measured_psi"))
        for r in regulator_records
        if abs(float(r.get("setpoint_psi", -1e9)) - min(setpoints)) <= tol_psi
    ]
    high_candidates = [
        float(r.get("measured_psi"))
        for r in regulator_records
        if abs(float(r.get("setpoint_psi", -1e9)) - max(setpoints)) <= tol_psi
    ]

    if low_candidates:
        low_measured = min(low_candidates)
        if low_measured > float(spec.regulator_min_allowed_psi):
            fails.append(
                {
                    "type": "regulator_min_pressure_too_high",
                    "measured_psi": low_measured,
                    "limit_psi": float(spec.regulator_min_allowed_psi),
                }
            )

    if high_candidates:
        high_measured = max(high_candidates)
        if high_measured < float(spec.regulator_max_allowed_psi):
            fails.append(
                {
                    "type": "regulator_max_pressure_too_low",
                    "measured_psi": high_measured,
                    "limit_psi": float(spec.regulator_max_allowed_psi),
                }
            )

    return {"ok": len(fails) == 0, "fails": fails, "covered_setpoints_psi": covered}


def evaluate_closing_times(
    records: List[Dict[str, Any]],
    spec: FunctionTestSpec = FunctionTestSpec(),
    *,
    regulator_records: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    records: list of dicts like:
      {"name": "ANN1", "type": "annular", "close_time_s": 52.3}
      {"name": "UBSR", "type": "ram", "close_time_s": 41.0}
    """
    fails = []
    for r in records:
        typ = str(r.get("type", "")).lower()
        if typ in ("annular", "ram"):
            if r.get("close_time_s") is None:
                fails.append({"name": r.get("name"), "type": typ, "reason": "missing_close_time_s"})
                continue

            t_close = float(r.get("close_time_s"))
            limit = _annular_limit(r, spec) if typ == "annular" else _ram_limit(r, spec)
            if t_close > limit:
                fails.append({"name": r.get("name"), "type": typ, "close_time_s": t_close, "limit_s": limit})
            continue

        # N-2753: tempo de abrir/fechar valvulas kill/choke <= tempo de fechamento de gaveta
        if typ == "valve":
            env = str(r.get("environment", "subsea")).lower()
            service = str(r.get("service", "")).lower()
            if env == "subsea" and service in ("kill", "choke", "kiv", "civ"):
                limit = float(spec.max_subsea_kill_choke_valve_time_s)
                for key in ("close_time_s", "open_time_s"):
                    if r.get(key) is None:
                        continue
                    t_op = float(r.get(key))
                    if t_op > limit:
                        fails.append(
                            {
                                "name": r.get("name"),
                                "type": typ,
                                "service": service,
                                "metric": key,
                                "time_s": t_op,
                                "limit_s": limit,
                            }
                        )

    regulator_eval = {"ok": True, "fails": [], "covered_setpoints_psi": []}
    must_validate_regulators = bool(spec.validate_regulators) or regulator_records is not None
    if must_validate_regulators:
        regulator_eval = _evaluate_regulators(regulator_records or [], spec)

    ok = len(fails) == 0 and bool(regulator_eval["ok"])
    if ok:
        reason = "ok"
    elif fails and regulator_eval["ok"]:
        reason = "closing_time_exceeds_limit"
    elif not fails and not regulator_eval["ok"]:
        reason = "regulator_criteria_not_met"
    else:
        reason = "closing_time_and_regulator_criteria_not_met"

    return {
        "ok": ok,
        "reason": reason,
        "details": {"fails": fails, "regulator": regulator_eval},
    }
