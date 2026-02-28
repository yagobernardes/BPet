# bop_twin/profiles/function_catalog.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal

Supply = Literal["HP", "LP"]


@dataclass(frozen=True)
class FunctionSpec:
    """
    Especificação mínima para gerar curvas por função hidráulica.
    - supply: se usa pressão alta (HP) ou baixa (LP)
    - V_act_m3: volume equivalente do nó do atuador/linha daquela função
    - valve_area_m2: área efetiva do caminho (equivalente da válvula/orifício)
    """
    name: str
    supply: Supply
    V_act_m3: float
    valve_area_m2: float


def get_default_function_catalog() -> Dict[str, FunctionSpec]:
    """
    Catálogo inicial (MVP). Valores de V_act_m3 e valve_area_m2 são placeholders
    calibráveis quando você tiver diâmetros/comprimentos/volumes reais.

    Você pode ajustar por função conforme documentos (NS-47 / diagramas POD/HPU).
    """
    # defaults "razoáveis" para começar
    V_small = 0.002   # 2 L  -> válvulas / circuitos pequenos
    V_med   = 0.005   # 5 L  -> rams/atuadores médios
    V_big   = 0.010   # 10 L -> anulares / grandes volumes

    A_small = 2e-5    # área efetiva pequena
    A_med   = 1e-4    # área efetiva média
    A_big   = 2e-4    # área efetiva grande

    cat = {
        # Anulares (normalmente HP para fechamento/anular)
        "UA": FunctionSpec("UA", supply="HP", V_act_m3=V_big, valve_area_m2=A_big),
        "LA": FunctionSpec("LA", supply="HP", V_act_m3=V_big, valve_area_m2=A_big),

        # Gavetas cisalhantes (HP)
        "UBSR": FunctionSpec("UBSR", supply="HP", V_act_m3=V_med, valve_area_m2=A_med),
        "LBSR": FunctionSpec("LBSR", supply="HP", V_act_m3=V_med, valve_area_m2=A_med),

        # Gavetas de tubo (muitas vezes LP ou HP dependendo do circuito; aqui deixei HP no MVP)
        "UPR": FunctionSpec("UPR", supply="HP", V_act_m3=V_med, valve_area_m2=A_med),
        "MPR": FunctionSpec("MPR", supply="HP", V_act_m3=V_med, valve_area_m2=A_med),
        "LPR": FunctionSpec("LPR", supply="HP", V_act_m3=V_med, valve_area_m2=A_med),

        # Válvulas submarinas (tipicamente volumes menores)
        "UIBV": FunctionSpec("UIBV", supply="LP", V_act_m3=V_small, valve_area_m2=A_small),
        "UOBV": FunctionSpec("UOBV", supply="LP", V_act_m3=V_small, valve_area_m2=A_small),
        "LIBV": FunctionSpec("LIBV", supply="LP", V_act_m3=V_small, valve_area_m2=A_small),
        "LOBV": FunctionSpec("LOBV", supply="LP", V_act_m3=V_small, valve_area_m2=A_small),

        "UIC": FunctionSpec("UIC", supply="LP", V_act_m3=V_small, valve_area_m2=A_small),
        "UOC": FunctionSpec("UOC", supply="LP", V_act_m3=V_small, valve_area_m2=A_small),
        "UIK": FunctionSpec("UIK", supply="LP", V_act_m3=V_small, valve_area_m2=A_small),
        "UOK": FunctionSpec("UOK", supply="LP", V_act_m3=V_small, valve_area_m2=A_small),

        "MIC": FunctionSpec("MIC", supply="LP", V_act_m3=V_small, valve_area_m2=A_small),
        "MOC": FunctionSpec("MOC", supply="LP", V_act_m3=V_small, valve_area_m2=A_small),
        "MIK": FunctionSpec("MIK", supply="LP", V_act_m3=V_small, valve_area_m2=A_small),
        "MOK": FunctionSpec("MOK", supply="LP", V_act_m3=V_small, valve_area_m2=A_small),

        "LIC": FunctionSpec("LIC", supply="LP", V_act_m3=V_small, valve_area_m2=A_small),
        "LOC": FunctionSpec("LOC", supply="LP", V_act_m3=V_small, valve_area_m2=A_small),
        "LIK": FunctionSpec("LIK", supply="LP", V_act_m3=V_small, valve_area_m2=A_small),
        "LOK": FunctionSpec("LOK", supply="LP", V_act_m3=V_small, valve_area_m2=A_small),
    }
    return cat