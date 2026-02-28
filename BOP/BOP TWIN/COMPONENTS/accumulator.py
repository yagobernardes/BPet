from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class AccumulatorParams:
    """
    Modelo 0D lumped de acumulador gás+fluido (politrópico simplificado).

    Convenção do MVP:
    - A pressão do nó do acumulador P [Pa] é estado do sistema (x).
    - A vazão líquida saindo do acumulador Q_out [m³/s] reduz o volume de fluido no acumulador.
    - O gás é comprimido/expandido politropicamente: P_g * V_g^n = const.
    - Quando o fluido sai, o volume de gás aumenta: V_g = V_g0 + (Vf0 - Vf)
    """
    name: str

    # Gás
    precharge_pa: float            # P0
    gas_volume_m3: float           # Vg0 (volume de gás na pré-carga)
    polytropic_n: float = 1.2      # n

    # Fluido disponível no acumulador (volume inicial de fluido "carregável")
    fluid_volume_m3: float = 0.0   # Vf0

    # Limites de segurança numérica (opcional)
    min_pressure_pa: float = 1e5   # 1 bar
    max_pressure_pa: float = 1e9

    def __post_init__(self):
        if self.precharge_pa <= 0:
            raise ValueError("precharge_pa deve ser > 0")
        if self.gas_volume_m3 <= 0:
            raise ValueError("gas_volume_m3 deve ser > 0")
        if self.polytropic_n <= 0:
            raise ValueError("polytropic_n deve ser > 0")
        if self.fluid_volume_m3 < 0:
            raise ValueError("fluid_volume_m3 não pode ser negativo")


class Accumulator:
    """
    Componente acumulador.

    Estado mínimo do componente no MVP:
    - P [Pa] (pressão do nó do acumulador)

    Obs.: Para modelar corretamente o volume de fluido restante, você pode:
    - (A) manter Vf como estado também
    - (B) integrar Vf externamente no sistema
    - (C) aproximar: P dinâmico via bulk modulus do sistema (não recomendado aqui)

    Aqui eu deixo pronto para (A): P e Vf.
    """

    def __init__(self, params: AccumulatorParams):
        self.p = params

    def initial_state(self, *, pressure_pa: Optional[float] = None) -> Dict[str, float]:
        """
        Estado inicial:
        - P: se não fornecido, inicia na pré-carga (pior caso) ou você passa uma pressão inicial real.
        - Vf: volume inicial de fluido disponível.
        """
        P0 = self.p.precharge_pa if pressure_pa is None else float(pressure_pa)
        return {"P": P0, "Vf": float(self.p.fluid_volume_m3)}

    def gas_pressure_from_Vg(self, Vg: float) -> float:
        # P * V^n = const = P0 * V0^n
        return self.p.precharge_pa * (self.p.gas_volume_m3 / Vg) ** self.p.polytropic_n

    def rhs(
        self,
        t: float,
        state: Dict[str, float],
        Q_out_m3s: float,
        *,
        Q_in_m3s: float = 0.0,
    ) -> Dict[str, float]:
        """
        Retorna derivadas do estado do acumulador.

        - Q_out_m3s: vazão saindo do nó do acumulador para o sistema (>=0 consome fluido)
        - Q_in_m3s: vazão entrando de volta no acumulador (>=0 recarrega)

        Dinâmica:
        dVf/dt = Q_in - Q_out

        Pressão:
        Calculamos P como função algébrica do volume de gás Vg:
          Vg = Vg0 + (Vf0 - Vf)
          P = P0 * (Vg0/Vg)^n

        Para usar ODE puro, tratamos P como "estado algébrico":
        - Aqui calculamos P instantaneamente e retornamos dP/dt = 0.
        - Alternativa: manter P como estado e derivar dP/dt via relação diferencial.
          (Para MVP, algébrico é mais estável e simples.)
        """
        Vf = float(state["Vf"])
        Vf0 = self.p.fluid_volume_m3

        dVf_dt = float(Q_in_m3s) - float(Q_out_m3s)

        # Atualiza pressão "algébrica" a partir do Vf atual (não integrando P)
        # Gás expande quando Vf diminui.
        Vg = self.p.gas_volume_m3 + (Vf0 - Vf)
        if Vg <= 1e-12:
            Vg = 1e-12  # guarda numérica

        P = self.gas_pressure_from_Vg(Vg)
        # Clamps de sanidade
        if P < self.p.min_pressure_pa:
            P = self.p.min_pressure_pa
        if P > self.p.max_pressure_pa:
            P = self.p.max_pressure_pa

        # Mantém P coerente no state externo (quem chama pode sobrescrever)
        # Aqui retornamos dP/dt = 0 porque P é calculado por Vf.
        return {"P": 0.0, "Vf": dVf_dt}, P