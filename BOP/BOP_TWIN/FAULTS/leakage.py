from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
from bop_twin.faults.faults_base import Fault

@dataclass
class LeakageFault(Fault):
    CdA_leak_m2: float = 0.0

    def apply(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        cfg.setdefault("fault_runtime", {})
        cfg["fault_runtime"]["CdA_leak_m2"] = float(self.CdA_leak_m2)
        return cfg