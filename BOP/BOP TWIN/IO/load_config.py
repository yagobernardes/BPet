from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, Union


class ConfigError(ValueError):
    """Erro relacionado à configuração do BOP (JSON inválido ou incompleto)."""
    pass

def _read_json(path: Union[str, Path]) -> Dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Arquivo não encontrado: {path}")
    if path.suffix.lower() != ".json":
        raise ConfigError(f"O arquivo deve ser .json. Recebido: {path.name}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Erro ao decodificar JSON: {e}")
    if not isinstance(data, dict):
        raise ConfigError("O JSON deve conter um objeto no nível raiz.")
    return data


def _require_field(cfg: Dict[str, Any], path: str):
    """Verifica se o campo existe (ex: 'fluid.rho')."""
    current = cfg
    for key in path.split("."):
        if key not in current:
            raise ConfigError(f"Campo obrigatório ausente: {path}")
        current = current[key]
    return current


def _ensure_positive(value: float, field: str):
    if value <= 0:
        raise ConfigError(f"O campo '{field}' deve ser maior que zero.")


def _validate_minimum_structure(cfg: Dict[str, Any]) -> None:

    # Meta
    _require_field(cfg, "meta.name")

    # Fluido
    rho = _require_field(cfg, "fluid.rho")
    bulk = _require_field(cfg, "fluid.bulk_modulus")

    _ensure_positive(float(rho), "fluid.rho")
    _ensure_positive(float(bulk), "fluid.bulk_modulus")

    # Acumulador
    accum = _require_field(cfg, "accumulators")
    if not isinstance(accum, dict) or len(accum) == 0:
        raise ConfigError("É necessário pelo menos 1 acumulador.")

    # Válvula
    valves = _require_field(cfg, "valves")
    if not isinstance(valves, dict) or len(valves) == 0:
        raise ConfigError("É necessário pelo menos 1 válvula.")

    # Atuador
    actuators = _require_field(cfg, "actuators")
    if not isinstance(actuators, dict) or len(actuators) == 0:
        raise ConfigError("É necessário pelo menos 1 atuador.")


def _normalize_numbers(cfg: Dict[str, Any]) -> None:
    """Converte valores numéricos para float quando necessário."""

    cfg["fluid"]["rho"] = float(cfg["fluid"]["rho"])
    cfg["fluid"]["bulk_modulus"] = float(cfg["fluid"]["bulk_modulus"])

    for name, acc in cfg.get("accumulators", {}).items():
        if "gas_precharge_psi" in acc and acc["gas_precharge_psi"] is not None:
            acc["gas_precharge_psi"] = float(acc["gas_precharge_psi"])

        if "gas_volume_l" in acc and acc["gas_volume_l"] is not None:
            acc["gas_volume_l"] = float(acc["gas_volume_l"])

        if "fluid_volume_l" in acc and acc["fluid_volume_l"] is not None:
            acc["fluid_volume_l"] = float(acc["fluid_volume_l"])

        acc.setdefault("polytropic_n", 1.2)

    for name, valve in cfg.get("valves", {}).items():
        if "cd" in valve and valve["cd"] is not None:
            valve["cd"] = float(valve["cd"])
        if "area_m2" in valve and valve["area_m2"] is not None:
            valve["area_m2"] = float(valve["area_m2"])
        valve.setdefault("tau_open_s", 0.15)

    for name, act in cfg.get("actuators", {}).items():
        for key in ["piston_area_m2", "stroke_m", "mass_kg",
                    "friction_coulomb_n", "friction_viscous_n_per_ms"]:
            if key in act and act[key] is not None:
                act[key] = float(act[key])

        act.setdefault("friction_coulomb_n", 0.0)
        act.setdefault("friction_viscous_n_per_ms", 0.0)


def load_config(path: Union[str, Path], convert_to_SI: bool = False) -> Dict[str, Any]:
    cfg = _read_json(path)
    _validate_minimum_structure(cfg)
    _normalize_numbers(cfg)

    if convert_to_SI:
        from bop_twin.core.units import psi_to_pa, liter_to_m3
        for acc in cfg.get("accumulators", {}).values():
            if acc.get("gas_precharge_psi") is not None:
                acc["gas_precharge_pa"] = psi_to_pa(acc["gas_precharge_psi"])
            if acc.get("gas_volume_l") is not None:
                acc["gas_volume_m3"] = liter_to_m3(acc["gas_volume_l"])
    return cfg