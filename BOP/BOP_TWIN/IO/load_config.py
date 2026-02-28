from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, Union

from bop_twin.core.units import psi_to_pa, gal_to_m3, liter_to_m3, inch_to_m

class ConfigError(ValueError):
    pass

def _read_json(path: Union[str, Path]) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Arquivo não encontrado: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ConfigError(f"JSON inválido em {p}: {e}") from e
    if not isinstance(data, dict):
        raise ConfigError("Topo do JSON deve ser um objeto.")
    return data

def _get(cfg: Dict[str, Any], key: str) -> Any:
    if key not in cfg:
        raise ConfigError(f"Campo obrigatório ausente: {key}")
    return cfg[key]

def _ensure_minimum(cfg: Dict[str, Any]) -> None:
    _get(cfg, "meta")
    _get(cfg["meta"], "name")

    _get(cfg, "fluid")
    _get(cfg["fluid"], "rho")
    _get(cfg["fluid"], "bulk_modulus")

    _get(cfg, "accumulators")
    if not isinstance(cfg["accumulators"], dict) or len(cfg["accumulators"]) == 0:
        raise ConfigError("'accumulators' deve ser dict com pelo menos 1 item.")

    _get(cfg, "valves")
    if not isinstance(cfg["valves"], dict) or len(cfg["valves"]) == 0:
        raise ConfigError("'valves' deve ser dict com pelo menos 1 item.")

    _get(cfg, "actuators")
    if not isinstance(cfg["actuators"], dict) or len(cfg["actuators"]) == 0:
        raise ConfigError("'actuators' deve ser dict com pelo menos 1 item.")

def load_config(path: Union[str, Path], *, convert_to_SI: bool = False) -> Dict[str, Any]:
    cfg = _read_json(path)
    _ensure_minimum(cfg)

    # Normaliza números básicos
    cfg["fluid"]["rho"] = float(cfg["fluid"]["rho"])
    cfg["fluid"]["bulk_modulus"] = float(cfg["fluid"]["bulk_modulus"])

    if convert_to_SI:
        # Exemplo: se quiser duplicar para SI sem perder originais:
        cfg["fluid"]["bulk_modulus_pa"] = cfg["fluid"]["bulk_modulus"]  # já está em Pa no seu json
        cfg["fluid"]["rho_kg_m3"] = cfg["fluid"]["rho"]

        # Converte RAMS se existirem
        rams = cfg.get("rams", {})
        if isinstance(rams, dict):
            def convert_ram(ram: dict):
                if ram.get("main_piston_diameter_in") is not None:
                    ram["main_piston_diameter_m"] = inch_to_m(float(ram["main_piston_diameter_in"]))
                if ram.get("rod_diameter_in") is not None:
                    ram["rod_diameter_m"] = inch_to_m(float(ram["rod_diameter_in"]))
                if ram.get("closing_volume_gal") is not None:
                    ram["closing_volume_m3"] = gal_to_m3(float(ram["closing_volume_gal"]))
                if ram.get("actuation_pressure_psi") is not None:
                    ram["actuation_pressure_pa"] = psi_to_pa(float(ram["actuation_pressure_psi"]))
                if ram.get("high_pressure_psi") is not None:
                    ram["high_pressure_pa"] = psi_to_pa(float(ram["high_pressure_psi"]))
                if ram.get("main_piston_diameter_m") is not None:
                    d = ram["main_piston_diameter_m"]
                    ram["main_piston_area_m2"] = math.pi * d * d / 4.0

            for k, ram in rams.items():
                if isinstance(ram, dict):
                    convert_ram(ram)
            pipe_rams = rams.get("pipe_rams")
            if isinstance(pipe_rams, dict):
                for _, pr in pipe_rams.items():
                    if isinstance(pr, dict):
                        convert_ram(pr)

        # Converte acumuladores/atuadores se você preencher esses campos no JSON
        for _, acc in cfg.get("accumulators", {}).items():
            if acc.get("gas_precharge_psi") is not None:
                acc["gas_precharge_pa"] = psi_to_pa(float(acc["gas_precharge_psi"]))
            if acc.get("gas_volume_l") is not None:
                acc["gas_volume_m3"] = liter_to_m3(float(acc["gas_volume_l"]))
            if acc.get("fluid_volume_l") is not None:
                acc["fluid_volume_m3"] = liter_to_m3(float(acc["fluid_volume_l"]))

    return cfg