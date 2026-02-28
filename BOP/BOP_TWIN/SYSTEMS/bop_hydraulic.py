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
    gas_volume_fraction: float = 0.0
    V_acc_line_m3: float = 0.0
    V_act_line_m3: float = 0.0
    acc_structure_compliance_m3_per_pa: float = 0.0
    act_structure_compliance_m3_per_pa: float = 0.0
    line_resistance_pa_s_per_m3: float = 0.0


class BOPHydraulicMVP:
    """
    States: y=[P_acc, P_act] in Pa.
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

    def effective_bulk_modulus_pa(self, p_node_pa: float) -> float:
        """
        Effective bulk modulus including optional free-gas fraction
        (Wood's equation style mixture approximation).
        """
        beta_liq = max(float(self.hp.bulk_modulus), 1e3)
        phi = float(np.clip(self.hp.gas_volume_fraction, 0.0, 0.95))
        if phi <= 0.0:
            return beta_liq

        p_abs = max(float(p_node_pa), 1e4)
        inv_beta_eff = ((1.0 - phi) / beta_liq) + (phi / p_abs)
        return 1.0 / max(inv_beta_eff, 1e-18)

    def node_capacitance_m3_per_pa(
        self,
        node_volume_m3: float,
        p_node_pa: float,
        structural_compliance_m3_per_pa: float,
    ) -> float:
        beta_eff = self.effective_bulk_modulus_pa(p_node_pa)
        fluid_cap = max(float(node_volume_m3), 1e-9) / max(beta_eff, 1e3)
        struct_cap = max(float(structural_compliance_m3_per_pa), 0.0)
        return max(fluid_cap + struct_cap, 1e-15)

    def apply_line_resistance_limit(self, q_m3s: float, dP_pa: float) -> float:
        r_line = float(self.hp.line_resistance_pa_s_per_m3)
        if r_line <= 0.0:
            return float(q_m3s)
        q_limit = abs(float(dP_pa)) / r_line
        return float(np.sign(q_m3s) * min(abs(float(q_m3s)), q_limit))

    def rhs(self, t: float, y):
        P_acc = float(y[0])
        P_act = float(y[1])

        opening = float(self.opening_fun(t))
        dP_acc_to_act = P_acc - P_act
        Q = self.valve.flow_m3s(P_acc, P_act, rho=self.hp.rho, opening=opening)
        Q = self.apply_line_resistance_limit(Q, dP_acc_to_act)
        Q_leak = self.leak_flow_m3s(P_act)

        V_acc_total = float(self.hp.V_acc_eff_m3) + float(self.hp.V_acc_line_m3)
        V_act_total = float(self.hp.V_act_m3) + float(self.hp.V_act_line_m3)

        C_acc = self.node_capacitance_m3_per_pa(
            node_volume_m3=V_acc_total,
            p_node_pa=P_acc,
            structural_compliance_m3_per_pa=float(self.hp.acc_structure_compliance_m3_per_pa),
        )
        C_act = self.node_capacitance_m3_per_pa(
            node_volume_m3=V_act_total,
            p_node_pa=P_act,
            structural_compliance_m3_per_pa=float(self.hp.act_structure_compliance_m3_per_pa),
        )

        dPacc_dt = (-Q) / C_acc
        dPact_dt = (Q - Q_leak) / C_act
        return [dPacc_dt, dPact_dt]


def build_system_from_cfg(cfg: dict, *, opening_fun=None, leak_CdA_m2: float = 0.0) -> BOPHydraulicMVP:
    rho = float(cfg["fluid"]["rho"])
    beta = float(cfg["fluid"]["bulk_modulus"])

    hyd = cfg.get("hydraulics", {})
    V_acc_eff = float(hyd.get("V_acc_eff_m3", 0.02))  # default 20 L
    V_act = float(hyd.get("V_act_m3", 0.005))  # default 5 L
    gas_fraction = float(cfg.get("fluid", {}).get("gas_volume_fraction", 0.0))

    hp = LumpedHydraulicParams(
        rho=rho,
        bulk_modulus=beta,
        V_acc_eff_m3=V_acc_eff,
        V_act_m3=V_act,
        CdA_leak_m2=float(leak_CdA_m2),
        gas_volume_fraction=gas_fraction,
        V_acc_line_m3=float(hyd.get("V_acc_line_m3", 0.0)),
        V_act_line_m3=float(hyd.get("V_act_line_m3", 0.0)),
        acc_structure_compliance_m3_per_pa=float(hyd.get("acc_structure_compliance_m3_per_pa", 0.0)),
        act_structure_compliance_m3_per_pa=float(hyd.get("act_structure_compliance_m3_per_pa", 0.0)),
        line_resistance_pa_s_per_m3=float(hyd.get("line_resistance_pa_s_per_m3", 0.0)),
    )

    first_valve_name = next(iter(cfg["valves"].keys()))
    vcfg = cfg["valves"][first_valve_name]
    valve = OrificeValve(
        OrificeValveParams(
            name=first_valve_name,
            cd=float(vcfg.get("cd", 0.62)),
            area_m2=float(vcfg.get("area_m2", 1e-4)),
            min_delta_p_pa=float(vcfg.get("min_delta_p_pa", 0.0)),
            yield_stress_pa=float(vcfg.get("yield_stress_pa", cfg.get("fluid", {}).get("yield_stress_pa", 0.0))),
            hydraulic_diameter_m=float(vcfg.get("hydraulic_diameter_m", 0.01)),
            equivalent_length_m=float(vcfg.get("equivalent_length_m", 1.0)),
            transmission_gain=float(vcfg.get("transmission_gain", 1.0)),
            inertia_dissipation_ratio=float(vcfg.get("inertia_dissipation_ratio", 1.0)),
            attenuation_alpha=float(vcfg.get("attenuation_alpha", 0.0)),
            allow_reverse_flow=bool(vcfg.get("allow_reverse_flow", False)),
            reverse_flow_gain=float(vcfg.get("reverse_flow_gain", 1.0)),
        )
    )

    return BOPHydraulicMVP(hp, valve, opening_fun=opening_fun)
