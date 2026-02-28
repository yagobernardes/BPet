from __future__ import annotations

from dataclasses import dataclass
import numpy as np

@dataclass
class OrificeValveParams:
    name: str
    cd: float = 0.62
    area_m2: float = 1e-4
    min_opening: float = 0.0
    max_opening: float = 1.0

class OrificeValve:
    def __init__(self, params: OrificeValveParams):
        self.p = params

    def flow_m3s(self, p_up_pa: float, p_dn_pa: float, rho: float, opening: float) -> float:
        opening = float(np.clip(opening, self.p.min_opening, self.p.max_opening))
        dP = max(float(p_up_pa) - float(p_dn_pa), 0.0)
        A = self.p.area_m2 * opening
        if dP <= 0.0 or A <= 0.0:
            return 0.0
        return self.p.cd * A * np.sqrt(2.0 * dP / float(rho))