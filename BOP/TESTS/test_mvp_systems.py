# tests/test_mvp_systems.py
import numpy as np

from bop_twin.io.load_config import load_config
from bop_twin.core.ode import integrate_ode
from bop_twin.systems.bop_hydraulic import build_system_from_cfg
from bop_twin.profiles.commands import step_opening


def main():
    cfg = load_config("configs/ns47.json", convert_to_SI=False)

    # ============================================================
    # 1) Teste de pressurização (degrau na válvula)
    # ============================================================
    opening = step_opening(t_step=2.0, level=1.0)
    sys_ok = build_system_from_cfg(cfg, opening_fun=opening, leak_CdA_m2=0.0)

    y0 = [207e5, 1e5]  # [P_acc, P_act]
    t_eval = np.arange(0, 30.0 + 1e-12, 0.05)

    print("🔬 Rodando MVP: acumulador->valvula->atuador")
    sol = integrate_ode(
        fun=sys_ok.rhs,
        y0=y0,
        t_span=(0.0, 30.0),
        t_eval=t_eval,
        method="RK45",
        verbose=False
    )

    print("✅ OK | P_acc_final(bar)=", sol["y"][0, -1] / 1e5,
          "P_act_final(bar)=", sol["y"][1, -1] / 1e5)

    # ============================================================
    # 2) Hold test (5 min) para sistema 2-estados
    #    - Válvula fechada (hold)
    #    - Vazamento no nó do atuador
    #    - Avaliamos queda de pressão em P_act
    # ============================================================
    t_end = 5.0 * 60.0
    t_eval_hold = np.arange(0.0, t_end + 1e-12, 0.5)

    # hold: válvula fechada
    sys_leak_hold = build_system_from_cfg(
        cfg,
        opening_fun=lambda t: 0.0,
        leak_CdA_m2=5e-7
    )

    # estado inicial do hold: pressurizado nos dois nós
    y0_hold = [207e5, 207e5]  # [P_acc, P_act]

    sol_hold = integrate_ode(
        fun=sys_leak_hold.rhs,
        y0=y0_hold,
        t_span=(0.0, t_end),
        t_eval=t_eval_hold,
        method="RK45",
        verbose=False
    )

    P0 = float(sol_hold["y"][1, 0])     # P_act inicial
    Pend = float(sol_hold["y"][1, -1])  # P_act final
    delta_p_percent = (P0 - Pend) / P0 * 100.0

    # Critério genérico: <= 1% em 5 min (ajuste conforme seu critério do Anexo A)
    passed = delta_p_percent <= 1.0

    print(f"Hold 5 min (P_act) → ΔP={delta_p_percent:.3f}% → {'PASS' if passed else 'FAIL'}")


if __name__ == "__main__":
    main()