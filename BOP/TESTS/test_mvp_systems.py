import numpy as np

from bop_twin.io.load_config import load_config
from bop_twin.core.ode import integrate_ode, run_hold_test
from bop_twin.systems.bop_hydraulic import build_system_from_cfg
from bop_twin.profiles.commands import step_opening

def main():
    cfg = load_config("configs/ns47.json", convert_to_SI=False)

    opening = step_opening(t_step=2.0, level=1.0)
    sys_ok = build_system_from_cfg(cfg, opening_fun=opening, leak_CdA_m2=0.0)

    y0 = [207e5, 1e5]
    t_eval = np.arange(0, 30.0 + 1e-12, 0.05)

    print("🔬 Rodando MVP: acumulador->valvula->atuador")
    sol = integrate_ode(fun=sys_ok.rhs, y0=y0, t_span=(0, 30.0), t_eval=t_eval, method="RK45", verbose=False)
    print("✅ OK | P_acc_final(bar)=", sol["y"][0, -1] / 1e5, "P_act_final(bar)=", sol["y"][1, -1] / 1e5)

    sys_leak = build_system_from_cfg(cfg, opening_fun=lambda t: 1.0, leak_CdA_m2=5e-7)

    def hold_fun(t, y):
        return sys_leak.rhs(t, y)

    res = run_hold_test(hold_fun, p0_pa=207e5, t_hold_min=5.0)
    print(f"Hold 5 min → ΔP={res['delta_p_percent']:.3f}% → {'PASS' if res['pass'] else 'FAIL'}")

if __name__ == "__main__":
    main()