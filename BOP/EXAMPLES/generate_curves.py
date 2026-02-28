# examples/generate_curves.py
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np

from bop_twin.io.load_config import load_config
from bop_twin.core.ode import integrate_ode
from bop_twin.core.units import psi_to_pa
from bop_twin.io.export import export_csv
from bop_twin.profiles.function_catalog import get_default_function_catalog
from bop_twin.components.valve import OrificeValve, OrificeValveParams
from bop_twin.systems.bop_hydraulic import BOPHydraulicMVP, LumpedHydraulicParams


def parse_args():
    parser = argparse.ArgumentParser(description="Generate synthetic hydraulic curves per BOP function.")
    parser.add_argument(
        "--functions",
        nargs="*",
        default=None,
        help="Function IDs to generate (e.g., UA LA UBSR). Default: all catalog.",
    )
    parser.add_argument(
        "--directions",
        nargs="*",
        default=["surface_to_well", "well_to_surface"],
        choices=["surface_to_well", "well_to_surface"],
        help="Flow direction scenarios to generate.",
    )
    parser.add_argument(
        "--max-functions",
        type=int,
        default=0,
        help="If >0, generate only first N functions after filtering.",
    )
    parser.add_argument("--t-press", type=float, default=30.0, help="Pressurization duration in seconds.")
    parser.add_argument("--t-hold", type=float, default=300.0, help="Hold duration in seconds.")
    parser.add_argument("--t-bleed", type=float, default=60.0, help="Bleed duration in seconds.")
    parser.add_argument("--dt-fast", type=float, default=0.05, help="Time step used for pressurization output.")
    parser.add_argument("--dt-hold", type=float, default=0.5, help="Time step used for hold output.")
    parser.add_argument("--dt-bleed", type=float, default=0.1, help="Time step used for bleed output.")
    parser.add_argument("--ode-method", type=str, default="BDF", help="ODE method (e.g., RK45, BDF, LSODA).")
    parser.add_argument("--rtol", type=float, default=1e-4, help="Relative tolerance for ODE solver.")
    parser.add_argument("--atol", type=float, default=1e-7, help="Absolute tolerance for ODE solver.")
    return parser.parse_args()


def get_supply_pressures_pa(cfg: dict) -> dict:
    hyd = cfg.get("hydraulics", {})
    hp_psi = float(hyd.get("hp_supply_pressure_psi", 3500.0))
    lp_psi = float(hyd.get("lp_supply_pressure_psi", 1500.0))
    ret_psi = float(hyd.get("return_pressure_psi", 14.7))
    return {
        "HP": float(psi_to_pa(hp_psi)),
        "LP": float(psi_to_pa(lp_psi)),
        "RET": float(psi_to_pa(ret_psi)),
    }


def build_mvp_for_function(
    cfg: dict,
    *,
    V_act_m3: float,
    valve_area_m2: float,
    opening_fun,
    CdA_leak_m2: float = 0.0,
):
    rho = float(cfg["fluid"]["rho"])
    beta = float(cfg["fluid"]["bulk_modulus"])
    V_acc_eff = float(cfg.get("hydraulics", {}).get("V_acc_eff_m3", 0.02))

    hp = LumpedHydraulicParams(
        rho=rho,
        bulk_modulus=beta,
        V_acc_eff_m3=V_acc_eff,
        V_act_m3=float(V_act_m3),
        CdA_leak_m2=float(CdA_leak_m2),
    )

    vcfg = cfg.get("valves", {}).get("directional_main", {})
    valve = OrificeValve(
        OrificeValveParams(
            name="directional_equivalent",
            cd=float(vcfg.get("cd", 0.62)),
            area_m2=float(valve_area_m2),
            allow_reverse_flow=bool(vcfg.get("allow_reverse_flow", True)),
            reverse_flow_gain=float(vcfg.get("reverse_flow_gain", 1.0)),
        )
    )

    return BOPHydraulicMVP(hp, valve, opening_fun=opening_fun)


def main():
    args = parse_args()
    cfg = load_config("configs/ns47.json", convert_to_SI=False)
    supplies = get_supply_pressures_pa(cfg)
    cat = get_default_function_catalog()

    if args.functions:
        allowed = {str(x).upper() for x in args.functions}
        cat = {k: v for k, v in cat.items() if k.upper() in allowed}
    if args.max_functions > 0:
        cat = dict(list(cat.items())[: int(args.max_functions)])

    out_dir = Path("out/generated")
    out_dir.mkdir(parents=True, exist_ok=True)

    def opening_step(t, t_step=1.0):
        return 1.0 if t >= t_step else 0.0

    t_press = float(args.t_press)
    t_hold = float(args.t_hold)
    t_bleed = float(args.t_bleed)

    dt_fast = float(args.dt_fast)
    dt_hold = float(args.dt_hold)
    dt_bleed = float(args.dt_bleed)

    scenarios = [
        ("healthy", 0.0),
        ("leak_small", 5e-9),
        ("leak_big", 5e-8),
    ]

    bleed_scenarios = [
        ("bleed", 2e-7),
    ]

    for fname, spec in cat.items():
        func_dir = out_dir / fname
        func_dir.mkdir(parents=True, exist_ok=True)

        P_supply = supplies[spec.supply]
        P_ret = supplies["RET"]
        direction_setups = []
        if "surface_to_well" in args.directions:
            direction_setups.append(("surface_to_well", P_supply, P_ret))
        if "well_to_surface" in args.directions:
            direction_setups.append(("well_to_surface", P_ret, P_supply))

        for direction_name, p_acc0, p_act0 in direction_setups:
            for sc_name, leak_CdA in scenarios:
                sys_press = build_mvp_for_function(
                    cfg,
                    V_act_m3=spec.V_act_m3,
                    valve_area_m2=spec.valve_area_m2,
                    opening_fun=lambda t: opening_step(t, 1.0),
                    CdA_leak_m2=0.0,
                )

                y0_press = [p_acc0, p_act0]
                t_eval_press = np.arange(0.0, t_press + 1e-12, dt_fast)

                sol_press = integrate_ode(
                    fun=sys_press.rhs,
                    y0=y0_press,
                    t_span=(0.0, t_press),
                    t_eval=t_eval_press,
                    method=args.ode_method,
                    rtol=args.rtol,
                    atol=args.atol,
                    verbose=False,
                )

                export_csv(
                    func_dir / f"{fname}_{direction_name}_press_{sc_name}.csv",
                    sol_press["t"],
                    sol_press["y"],
                    headers=["P_acc_pa", "P_act_pa"],
                )

                sys_hold = build_mvp_for_function(
                    cfg,
                    V_act_m3=spec.V_act_m3,
                    valve_area_m2=spec.valve_area_m2,
                    opening_fun=lambda t: 0.0,
                    CdA_leak_m2=float(leak_CdA),
                )

                y0_hold = [float(sol_press["y"][0, -1]), float(sol_press["y"][1, -1])]
                t_eval_hold = np.arange(0.0, t_hold + 1e-12, dt_hold)

                sol_hold = integrate_ode(
                    fun=sys_hold.rhs,
                    y0=y0_hold,
                    t_span=(0.0, t_hold),
                    t_eval=t_eval_hold,
                    method=args.ode_method,
                    rtol=args.rtol,
                    atol=args.atol,
                    verbose=False,
                )

                export_csv(
                    func_dir / f"{fname}_{direction_name}_hold_{sc_name}.csv",
                    sol_hold["t"],
                    sol_hold["y"],
                    headers=["P_acc_pa", "P_act_pa"],
                )

            for sc_name, bleed_CdA in bleed_scenarios:
                y0_bleed = [P_supply, P_supply]
                sys_bleed = build_mvp_for_function(
                    cfg,
                    V_act_m3=spec.V_act_m3,
                    valve_area_m2=spec.valve_area_m2,
                    opening_fun=lambda t: 0.0,
                    CdA_leak_m2=float(bleed_CdA),
                )

                t_eval_bleed = np.arange(0.0, t_bleed + 1e-12, dt_bleed)
                sol_bleed = integrate_ode(
                    fun=sys_bleed.rhs,
                    y0=y0_bleed,
                    t_span=(0.0, t_bleed),
                    t_eval=t_eval_bleed,
                    method=args.ode_method,
                    rtol=args.rtol,
                    atol=args.atol,
                    verbose=False,
                )

                export_csv(
                    func_dir / f"{fname}_{direction_name}_bleed_{sc_name}.csv",
                    sol_bleed["t"],
                    sol_bleed["y"],
                    headers=["P_acc_pa", "P_act_pa"],
                )

    print("Curvas geradas em: out/generated/<FUNCAO>/")


if __name__ == "__main__":
    main()
