from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from bop_twin.components.valve import OrificeValve, OrificeValveParams

@dataclass
class LumpedHydraulicParams:
    rho: float
    bulk_modulus: float
    V_acc_eff_m3: float
    V_act_m3: float
    p_atm_pa: float = 1e5
    CdA_leak_m2: float = 0.0

class BOPHydraulicMVP:
    """
    Estados: y=[P_acc, P_act] em Pa
    """
    def __init__(self, hp: LumpedHydraulicParams, valve: OrificeValve, opening_fun=None):
        self.hp = hp
        self.valve = valve
        self.opening_fun = opening_fun or (lambda t: 1.0)

    def leak_flow_m3s(self, p_act_pa: float) -> float:
        if self.hp.CdA_leak_m2 <= 0:
            return 0.0
        dP = max(float(p_act_pa) - self.hp.p_atm_pa, 0.0)
        if dP <= 0:
            return 0.0
        return self.hp.CdA_leak_m2 * np.sqrt(2.0 * dP / self.hp.rho)

    def rhs(self, t: float, y):
        P_acc = float(y[0])
        P_act = float(y[1])

        opening = float(self.opening_fun(t))
        Q = self.valve.flow_m3s(P_acc, P_act, rho=self.hp.rho, opening=opening)
        Q_leak = self.leak_flow_m3s(P_act)

        dPacc_dt = (self.hp.bulk_modulus / self.hp.V_acc_eff_m3) * (-Q)
        dPact_dt = (self.hp.bulk_modulus / self.hp.V_act_m3) * (Q - Q_leak)

        return [dPacc_dt, dPact_dt]

def build_system_from_cfg(cfg: dict, *, opening_fun=None, leak_CdA_m2: float = 0.0) -> BOPHydraulicMVP:
    rho = float(cfg["fluid"]["rho"])
    beta = float(cfg["fluid"]["bulk_modulus"])

    # defaults calibráveis (você substitui quando tiver diagrama)
    V_acc_eff = 0.02   # 20 L
    V_act = 0.005      # 5 L

    hp = LumpedHydraulicParams(
        rho=rho,
        bulk_modulus=beta,
        V_acc_eff_m3=V_acc_eff,
        V_act_m3=V_act,
        CdA_leak_m2=float(leak_CdA_m2),
    )

    first_valve_name = next(iter(cfg["valves"].keys()))
    vcfg = cfg["valves"][first_valve_name]
    valve = OrificeValve(
        OrificeValveParams(
            name=first_valve_name,
            cd=float(vcfg.get("cd", 0.62)),
            area_m2=float(vcfg.get("area_m2", 1e-4)),
        )
    )

    return BOPHydraulicMVP(hp, valve, opening_fun=opening_fun)