from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
from bop_twin.faults.faults_base import Fault

@dataclass
class PrechargeLossFault(Fault):
    factor: float = 0.8

    def apply(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        for _, acc in cfg.get("accumulators", {}).items():
            if acc.get("gas_precharge_psi") is not None:
                acc["gas_precharge_psi"] = float(acc["gas_precharge_psi"]) * float(self.factor)
        return cfg