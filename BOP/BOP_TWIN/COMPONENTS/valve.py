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
    min_delta_p_pa: float = 0.0
    yield_stress_pa: float = 0.0
    hydraulic_diameter_m: float = 0.01
    equivalent_length_m: float = 1.0
    transmission_gain: float = 1.0
    inertia_dissipation_ratio: float = 1.0
    attenuation_alpha: float = 0.0
    allow_reverse_flow: bool = False
    reverse_flow_gain: float = 1.0

class OrificeValve:
    def __init__(self, params: OrificeValveParams):
        self.p = params

    def _yield_delta_p_threshold_pa(self) -> float:
        # Circular tube wall stress: tau_w = dP * D / (4 * L)
        # Pressure transmission starts when tau_w > tau0 -> dP > 4*L*tau0/D
        if self.p.yield_stress_pa <= 0.0:
            return 0.0
        d = max(float(self.p.hydraulic_diameter_m), 1e-9)
        l = max(float(self.p.equivalent_length_m), 1e-9)
        return (4.0 * l * float(self.p.yield_stress_pa)) / d

    def flow_m3s(self, p_up_pa: float, p_dn_pa: float, rho: float, opening: float) -> float:
        opening = float(np.clip(opening, self.p.min_opening, self.p.max_opening))
        raw_dP = float(p_up_pa) - float(p_dn_pa)
        if not self.p.allow_reverse_flow:
            raw_dP = max(raw_dP, 0.0)

        direction = float(np.sign(raw_dP))
        dP = abs(raw_dP)
        A = self.p.area_m2 * opening
        if dP <= 0.0 or A <= 0.0 or direction == 0.0:
            return 0.0

        dP_threshold = max(float(self.p.min_delta_p_pa), self._yield_delta_p_threshold_pa())
        dP_effective = max(dP - dP_threshold, 0.0)
        if dP_effective <= 0.0:
            return 0.0

        q = self.p.cd * A * np.sqrt(2.0 * dP_effective / float(rho))

        gain = float(np.clip(self.p.transmission_gain, 0.0, 1.0))
        if direction < 0.0:
            gain *= max(float(self.p.reverse_flow_gain), 0.0)
        if self.p.attenuation_alpha > 0.0 and self.p.yield_stress_pa > 0.0:
            d = max(float(self.p.hydraulic_diameter_m), 1e-9)
            l = max(float(self.p.equivalent_length_m), 1e-9)
            tau_w = dP * d / (4.0 * l)
            bingham_like = float(self.p.yield_stress_pa) / max(tau_w, 1e-9)
            lambda_ratio = max(float(self.p.inertia_dissipation_ratio), 1e-9)
            attenuation = float(np.exp(-float(self.p.attenuation_alpha) * bingham_like / lambda_ratio))
            gain *= attenuation

        return direction * gain * q
