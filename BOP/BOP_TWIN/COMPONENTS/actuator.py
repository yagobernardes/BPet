from __future__ import annotations
from dataclasses import dataclass

@dataclass
class ActuatorVolumeParams:
    name: str
    V_m3: float  # volume compressível do nó do atuador

class ActuatorVolume:
    def __init__(self, p: ActuatorVolumeParams):
        self.p = p