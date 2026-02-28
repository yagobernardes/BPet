import numpy as np

from bop_twin.io.load_config import load_config
from bop_twin.core.ode import integrate_ode
from bop_twin.systems.bop_hydraulic import build_system_from_cfg
from bop_twin.io.export import export_csv
from bop_twin.profiles.commands import step_opening

cfg = load_config("configs/ns47.json", convert_to_SI=False)

opening = step_opening(t_step=1.0, level=1.0)
sys = build_system_from_cfg(cfg, opening_fun=opening, leak_CdA_m2=0.0)

y0 = [207e5, 1e5]
t_eval = np.arange(0, 60 + 1e-12, 0.1)

sol = integrate_ode(fun=sys.rhs, y0=y0, t_span=(0, 60), t_eval=t_eval)
export_csv("out/ns47_mvp.csv", sol["t"], sol["y"], headers=["P_acc_pa", "P_act_pa"])

print("✅ Exportado: out/ns47_mvp.csv")