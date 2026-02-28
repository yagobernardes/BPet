from __future__ import annotations

PSI_TO_PA = 6894.75729
GAL_TO_M3 = 0.003785411784
LITER_TO_M3 = 0.001
INCH_TO_M = 0.0254
LB_TO_KG = 0.45359237
DEG_TO_RAD = 0.01745329252

def psi_to_pa(psi: float | None) -> float | None:
    return psi * PSI_TO_PA if psi is not None else None

def pa_to_psi(pa: float | None) -> float | None:
    return pa / PSI_TO_PA if pa is not None else None

def gal_to_m3(gal: float | None) -> float | None:
    return gal * GAL_TO_M3 if gal is not None else None

def m3_to_gal(m3: float | None) -> float | None:
    return m3 / GAL_TO_M3 if m3 is not None else None

def liter_to_m3(liter: float | None) -> float | None:
    return liter * LITER_TO_M3 if liter is not None else None

def inch_to_m(inch: float | None) -> float | None:
    return inch * INCH_TO_M if inch is not None else None

def m_to_inch(m: float | None) -> float | None:
    return m / INCH_TO_M if m is not None else None

def lb_to_kg(lb: float | None) -> float | None:
    return lb * LB_TO_KG if lb is not None else None

def deg_to_rad(deg: float | None) -> float | None:
    return deg * DEG_TO_RAD if deg is not None else None

# Aliases (conveniência)
def convert_pressure(psi: float | None) -> float | None:
    return psi_to_pa(psi)

def convert_volume_gal(gal: float | None) -> float | None:
    return gal_to_m3(gal)

def convert_length_in(inch: float | None) -> float | None:
    return inch_to_m(inch)