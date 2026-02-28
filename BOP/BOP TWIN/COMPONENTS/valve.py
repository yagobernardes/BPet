import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from bop_twin.core.ode import integrate_ode, run_hold_test

# Exemplo simples: pressão caindo por vazamento constante
def simple_leak(t, y, CdA=1e-6, beta=1.4e9, V=0.35, rho=1000):
    P = y[0]
    Q_leak = CdA * np.sqrt(2 * max(P - 1e5, 0) / rho)
    dPdt = - (beta / V) * Q_leak
    return [dPdt]

print("🔬 Testando integrador ODE...")
sol = integrate_ode(
    fun=lambda t, y: simple_leak(t, y, CdA=5e-7),
    y0=[207e5],
    t_span=(0, 300),
    t_eval=np.arange(0, 301, 0.5),
    method="RK45",
    verbose=True
)

print(f"✅ Integração OK | Última pressão: {sol['y'][0,-1]/1e5:.1f} bar")
print(f"   Tempo total: {sol['t'][-1]:.1f} s")

# Teste do hold test helper
def hold_fun(t, y):
    return simple_leak(t, y, CdA=1e-8)  # quase saudável

result = run_hold_test(hold_fun, p0_pa=207e5, t_hold_min=5.0)
print(f"   Hold Test 5 min → ΔP = {result['delta_p_percent']:.3f}% → {'PASS' if result['pass'] else 'FAIL'}")