# bop_twin/systems/bop_hydraulic.py
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from bop_twin.components.valve import OrificeValve, OrificeValveParams


@dataclass
class LumpedHydraulicParams:
    """
    Modelo 0D/1D mínimo:
    - Nó do acumulador com volume equivalente compressível V_acc_eff
    - Nó do atuador com volume V_act
    - Conexão via válvula orifício
    - (Opcional) vazamento no nó do atuador

    Estados: y = [P_acc, P_act] em Pa
    """
    rho: float                 # kg/m3
    bulk_modulus: float        # Pa (beta)
    V_acc_eff_m3: float        # m3 (volume equivalente compressível do nó do acumulador)
    V_act_m3: float            # m3 (volume do cilindro/linha do atuador)
    p_atm_pa: float = 1e5

    # Leak model no nó do atuador: Q_leak = CdA_leak * sqrt(2*(P_act - p_atm)/rho)
    CdA_leak_m2: float = 0.0

    def __post_init__(self):
        if self.rho <= 0:
            raise ValueError("rho deve ser > 0")
        if self.bulk_modulus <= 0:
            raise ValueError("bulk_modulus deve ser > 0")
        if self.V_acc_eff_m3 <= 0:
            raise ValueError("V_acc_eff_m3 deve ser > 0")
        if self.V_act_m3 <= 0:
            raise ValueError("V_act_m3 deve ser > 0")
        if self.p_atm_pa <= 0:
            raise ValueError("p_atm_pa deve ser > 0")
        if self.CdA_leak_m2 < 0:
            raise ValueError("CdA_leak_m2 deve ser >= 0")


class BOPHydraulicMVP:
    """
    Sistema hidráulico mínimo: acumulador->valvula->atuador.
    Compatível com integrate_ode(fun(t,y), y0, ...)

    Controle:
    - opening(t): 0..1 (comando da válvula)
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
        """
        y = [P_acc, P_act]
        """
        P_acc = float(y[0])
        P_act = float(y[1])

        opening = float(self.opening_fun(t))
        Q = self.valve.flow_m3s(P_acc, P_act, rho=self.hp.rho, opening=opening)  # acum->atuador

        Q_leak = self.leak_flow_m3s(P_act)

        dPacc_dt = (self.hp.bulk_modulus / self.hp.V_acc_eff_m3) * (-Q)
        dPact_dt = (self.hp.bulk_modulus / self.hp.V_act_m3) * (Q - Q_leak)

        return [dPacc_dt, dPact_dt]


def build_system_from_cfg(cfg: dict, *, opening_fun=None, leak_CdA_m2: float = 0.0) -> BOPHydraulicMVP:
    """
    Constrói o sistema mínimo a partir do cfg carregado pelo load_config.

    Observação:
    - Como seu ns47.json ainda tem vários nulls, aqui usamos defaults seguros
      para V_acc_eff e V_act.
    - Depois você calibra usando dados reais.
    """
    rho = float(cfg["fluid"]["rho"])
    beta = float(cfg["fluid"]["bulk_modulus"])

    # Defaults MVP (calibráveis)
    V_acc_eff = 0.02   # m3 (~20 L) equivalente compressível do nó do acumulador
    V_act = 0.005      # m3 (~5 L) volume do nó do atuador

    # Puxar do cfg se existir (opcional)
    # Você pode criar no JSON: hydraulic_control_model_targets.control_hydraulics.accumulator_bank.total_volume_gal etc.
    # e depois converter no load_config.
    # Por enquanto deixa calibrável aqui.

    hp = LumpedHydraulicParams(
        rho=rho,
        bulk_modulus=beta,
        V_acc_eff_m3=V_acc_eff,
        V_act_m3=V_act,
        CdA_leak_m2=float(leak_CdA_m2),
    )

    # Usa a primeira válvula do cfg
    first_valve_name = next(iter(cfg["valves"].keys()))
    vcfg = cfg["valves"][first_valve_name]
    valve = OrificeValve(OrificeValveParams(
        name=first_valve_name,
        cd=float(vcfg.get("cd", 0.62)),
        area_m2=float(vcfg.get("area_m2", 1.0e-4)),
        tau_open_s=float(vcfg.get("tau_open_s", 0.15)),
    ))

    return BOPHydraulicMVP(hp, valve, opening_fun=opening_fun)