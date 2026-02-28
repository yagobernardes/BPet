# examples/test_mvp_system.py
import numpy as np
from bop_twin.io.load_config import load_config
from bop_twin.core.ode import integrate_ode, run_hold_test
from bop_twin.systems.bop_hydraulic import build_system_from_cfg

cfg = load_config("configs/ns47.json", convert_to_SI=False)

# Perfil de abertura: degrau em t=2s
def opening_fun(t):
    return 1.0 if t >= 2.0 else 0.0

# Sistema saudável (sem vazamento)
sys_ok = build_system_from_cfg(cfg, opening_fun=opening_fun, leak_CdA_m2=0.0)

# Condição inicial: acumulador alto, atuador baixo
y0 = [207e5, 1e5]  # Pa

print("🔬 Rodando MVP: acumulador->valvula->atuador...")
sol = integrate_ode(
    fun=sys_ok.rhs,
    y0=y0,
    t_span=(0, 30),
    t_eval=np.arange(0, 30.01, 0.05),
    method="RK45",
    verbose=True
)
print("✅ OK. Pressões finais [bar]:",
      sol["y"][0, -1] / 1e5, sol["y"][1, -1] / 1e5)

# Agora um hold test com vazamento pequeno no atuador
sys_leak = build_system_from_cfg(cfg, opening_fun=lambda t: 1.0, leak_CdA_m2=5e-7)

def hold_fun(t, y):
    return sys_leak.rhs(t, y)

result = run_hold_test(hold_fun, p0_pa=207e5, t_hold_min=5.0)
print(f"Hold 5 min → ΔP = {result['delta_p_percent']:.3f}% → {'PASS' if result['pass'] else 'FAIL'}")