# examples/generate_curves.py
from __future__ import annotations

import os
from pathlib import Path
import numpy as np

from bop_twin.io.load_config import load_config
from bop_twin.core.ode import integrate_ode
from bop_twin.core.units import psi_to_pa
from bop_twin.io.export import export_csv
from bop_twin.profiles.function_catalog import get_default_function_catalog
from bop_twin.components.valve import OrificeValve, OrificeValveParams
from bop_twin.systems.bop_hydraulic import BOPHydraulicMVP, LumpedHydraulicParams


def get_supply_pressures_pa(cfg: dict) -> dict:
    """
    Lê pressões do JSON em psi e converte para Pa.
    Se não existir no JSON, usa defaults.
    """
    hyd = cfg.get("hydraulics", {})
    hp_psi = float(hyd.get("hp_supply_pressure_psi", 3500.0))
    lp_psi = float(hyd.get("lp_supply_pressure_psi", 1500.0))
    ret_psi = float(hyd.get("return_pressure_psi", 14.7))  # ~1 atm
    return {
        "HP": float(psi_to_pa(hp_psi)),
        "LP": float(psi_to_pa(lp_psi)),
        "RET": float(psi_to_pa(ret_psi)),
    }


def build_mvp_for_function(cfg: dict, *, V_act_m3: float, valve_area_m2: float, opening_fun, CdA_leak_m2: float = 0.0):
    rho = float(cfg["fluid"]["rho"])
    beta = float(cfg["fluid"]["bulk_modulus"])

    # Volume equivalente do nó do acumulador (placeholder calibrável)
    # Você pode colocar isso no JSON também (hydraulics.V_acc_eff_m3)
    V_acc_eff = float(cfg.get("hydraulics", {}).get("V_acc_eff_m3", 0.02))  # 20 L

    hp = LumpedHydraulicParams(
        rho=rho,
        bulk_modulus=beta,
        V_acc_eff_m3=V_acc_eff,
        V_act_m3=float(V_act_m3),
        CdA_leak_m2=float(CdA_leak_m2),
    )

    valve = OrificeValve(OrificeValveParams(
        name="directional_equivalent",
        cd=0.62,
        area_m2=float(valve_area_m2),
    ))

    return BOPHydraulicMVP(hp, valve, opening_fun=opening_fun)


def main():
    cfg = load_config("configs/ns47.json", convert_to_SI=False)
    supplies = get_supply_pressures_pa(cfg)

    cat = get_default_function_catalog()

    out_dir = Path("out/generated")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Perfis
    def opening_step(t, t_step=1.0):
        return 1.0 if t >= t_step else 0.0

    # Tempos
    t_press = 30.0
    t_hold = 5.0 * 60.0
    t_bleed = 60.0

    dt_fast = 0.05
    dt_hold = 0.5
    dt_bleed = 0.1

    # Cenários simples
    scenarios = [
        ("healthy", 0.0, 0.0),      # (name, leak_CdA, bleed_CdA)
        ("leak_small", 5e-9, 0.0),
        ("leak_big", 5e-8, 0.0),
    ]

    # Bleed controlado (para gerar curva de depressurização)
    bleed_scenarios = [
        ("bleed", 0.0, 2e-7),
    ]

    for fname, spec in cat.items():
        func_dir = out_dir / fname
        func_dir.mkdir(parents=True, exist_ok=True)

        P_supply = supplies[spec.supply]
        P_ret = supplies["RET"]

        # ----------------------------
        # 1) Pressurização + Hold
        # ----------------------------
        for sc_name, leak_CdA, bleed_CdA in scenarios:
            # Pressurização: válvula abre em degrau, começa com atuador em retorno
            sys_press = build_mvp_for_function(
                cfg,
                V_act_m3=spec.V_act_m3,
                valve_area_m2=spec.valve_area_m2,
                opening_fun=lambda t: opening_step(t, 1.0),
                CdA_leak_m2=0.0,  # sem leak durante pressurização
            )

            y0_press = [P_supply, P_ret]  # [P_acc, P_act]
            t_eval_press = np.arange(0.0, t_press + 1e-12, dt_fast)

            sol_press = integrate_ode(
                fun=sys_press.rhs,
                y0=y0_press,
                t_span=(0.0, t_press),
                t_eval=t_eval_press,
                method="RK45",
                verbose=False
            )

            export_csv(
                func_dir / f"{fname}_press_{sc_name}.csv",
                sol_press["t"],
                sol_press["y"],
                headers=["P_acc_pa", "P_act_pa"]
            )

            # Hold: válvula fechada, leak opcional no atuador (para simular perda de pressão)
            sys_hold = build_mvp_for_function(
                cfg,
                V_act_m3=spec.V_act_m3,
                valve_area_m2=spec.valve_area_m2,
                opening_fun=lambda t: 0.0,      # fechado
                CdA_leak_m2=float(leak_CdA),     # leak no atuador
            )

            # começa do final da pressurização (estado pressurizado)
            y0_hold = [float(sol_press["y"][0, -1]), float(sol_press["y"][1, -1])]
            t_eval_hold = np.arange(0.0, t_hold + 1e-12, dt_hold)

            sol_hold = integrate_ode(
                fun=sys_hold.rhs,
                y0=y0_hold,
                t_span=(0.0, t_hold),
                t_eval=t_eval_hold,
                method="RK45",
                verbose=False
            )

            export_csv(
                func_dir / f"{fname}_hold_{sc_name}.csv",
                sol_hold["t"],
                sol_hold["y"],
                headers=["P_acc_pa", "P_act_pa"]
            )

        # ----------------------------
        # 2) Bleed (depressurização)
        # ----------------------------
        # Aqui a gente usa o "leak" como bleed controlado: CdA_bleed grande + válvula fechada
        for sc_name, leak_CdA, bleed_CdA in bleed_scenarios:
            # Começa pressurizado (usa supply)
            y0_bleed = [P_supply, P_supply]

            sys_bleed = build_mvp_for_function(
                cfg,
                V_act_m3=spec.V_act_m3,
                valve_area_m2=spec.valve_area_m2,
                opening_fun=lambda t: 0.0,            # fechado (hold), bleed é via CdA
                CdA_leak_m2=float(bleed_CdA),         # bleed controlado (depressurização)
            )

            t_eval_bleed = np.arange(0.0, t_bleed + 1e-12, dt_bleed)

            sol_bleed = integrate_ode(
                fun=sys_bleed.rhs,
                y0=y0_bleed,
                t_span=(0.0, t_bleed),
                t_eval=t_eval_bleed,
                method="RK45",
                verbose=False
            )

            export_csv(
                func_dir / f"{fname}_bleed_{sc_name}.csv",
                sol_bleed["t"],
                sol_bleed["y"],
                headers=["P_acc_pa", "P_act_pa"]
            )

    print("✅ Curvas geradas em: out/generated/<FUNÇÃO>/")


if __name__ == "__main__":
    main()