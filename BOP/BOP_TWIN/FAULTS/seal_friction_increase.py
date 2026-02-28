from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
from bop_twin.faults.faults_base import Fault

@dataclass
class SealFrictionIncreaseFault(Fault):
    actuator_name: str
    delta_coulomb_n: float = 0.0

    def apply(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        a = cfg.get("actuators", {}).get(self.actuator_name)
        if isinstance(a, dict):
            a["friction_coulomb_n"] = float(a.get("friction_coulomb_n", 0.0)) + float(self.delta_coulomb_n)
        return cfg