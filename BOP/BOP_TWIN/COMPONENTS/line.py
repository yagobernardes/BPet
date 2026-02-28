from __future__ import annotations
from dataclasses import dataclass

@dataclass
class LineParams:
    name: str
    V_m3: float = 0.0  # volume lumped
    # perdas poderão entrar depois (R, K, etc.)