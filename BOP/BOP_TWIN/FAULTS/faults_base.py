from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class Fault:
    name: str
    def apply(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        """Retorna cfg modificado (cópia ou in-place)."""
        return cfg