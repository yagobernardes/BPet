from __future__ import annotations

# ====================== CONSTANTES ======================
PSI_TO_PA = 6894.75729          # 1 psi = 6894.75729 Pa
GAL_TO_M3 = 0.003785411784      # 1 US gal = 0.003785411784 m³
LITER_TO_M3 = 0.001             # 1 L = 0.001 m³
INCH_TO_M = 0.0254              # 1 in = 0.0254 m
LB_TO_KG = 0.45359237           # 1 lb = 0.45359237 kg
DEG_TO_RAD = 0.01745329252      # 1 deg = π/180 rad

# ====================== FUNÇÕES ======================

def psi_to_pa(psi: float | None) -> float | None:
    """psi → Pa"""
    return psi * PSI_TO_PA if psi is not None else None

def pa_to_psi(pa: float | None) -> float | None:
    """Pa → psi"""
    return pa / PSI_TO_PA if pa is not None else None

def gal_to_m3(gal: float | None) -> float | None:
    """US gallon → m³"""
    return gal * GAL_TO_M3 if gal is not None else None

def m3_to_gal(m3: float | None) -> float | None:
    """m³ → US gallon"""
    return m3 / GAL_TO_M3 if m3 is not None else None

def liter_to_m3(liter: float | None) -> float | None:
    """Litro → m³"""
    return liter * LITER_TO_M3 if liter is not None else None

def inch_to_m(inch: float | None) -> float | None:
    """Polegada → metro"""
    return inch * INCH_TO_M if inch is not None else None

def m_to_inch(m: float | None) -> float | None:
    """Metro → polegada"""
    return m / INCH_TO_M if m is not None else None

def lb_to_kg(lb: float | None) -> float | None:
    """Libra → kg"""
    return lb * LB_TO_KG if lb is not None else None

def deg_to_rad(deg: float | None) -> float | None:
    """Grau → radiano"""
    return deg * DEG_TO_RAD if deg is not None else None

# Funções de conveniência para o modelo 0D/1D
def convert_pressure(psi: float | None) -> float | None:
    """Alias comum usado no load_config"""
    return psi_to_pa(psi)

def convert_volume_gal(gal: float | None) -> float | None:
    """Alias comum"""
    return gal_to_m3(gal)

def convert_length_in(inch: float | None) -> float | None:
    """Alias comum"""
    return inch_to_m(inch)