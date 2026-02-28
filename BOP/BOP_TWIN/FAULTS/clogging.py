from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
from bop_twin.faults.faults_base import Fault

@dataclass
class CloggingFault(Fault):
    valve_name: str
    area_factor: float = 0.5

    def apply(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        v = cfg.get("valves", {}).get(self.valve_name)
        if isinstance(v, dict) and v.get("area_m2") is not None:
            v["area_m2"] = float(v["area_m2"]) * float(self.area_factor)
        return cfg