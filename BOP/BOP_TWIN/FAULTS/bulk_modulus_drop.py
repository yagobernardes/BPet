from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
from bop_twin.faults.faults_base import Fault

@dataclass
class BulkModulusDropFault(Fault):
    factor: float = 0.8  # ex: 0.8 reduz 20%

    def apply(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        cfg["fluid"]["bulk_modulus"] = float(cfg["fluid"]["bulk_modulus"]) * float(self.factor)
        return cfg