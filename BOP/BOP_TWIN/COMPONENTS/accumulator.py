from __future__ import annotations
from dataclasses import dataclass

@dataclass
class AccumulatorLumpedParams:
    name: str
    V_eff_m3: float  # volume equivalente compressível do nó do acumulador

class AccumulatorLumped:
    def __init__(self, p: AccumulatorLumpedParams):
        self.p = p