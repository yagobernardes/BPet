from bop_twin.criteria.pressure_acceptance_v2 import (
    PressureTestSpec,
    evaluate_pressure_test,
)

from bop_twin.criteria.soak_test_acceptance import evaluate_soak_test
from bop_twin.criteria.function_test_acceptance import evaluate_closing_times


def validate_pressure_low(
    t,
    p,
    *,
    pressure_unit: str = "psi",
    rwp: float | None = None,
    bop_nominal_pressure_psi: float | None = None,
    fluid_density_kg_m3: float | None = None,
    lda_m: float | None = None,
):
    spec = PressureTestSpec(mode="low")
    return evaluate_pressure_test(
        t,
        p,
        spec,
        pressure_unit=pressure_unit,
        rwp_psi=rwp,
        bop_nominal_pressure_psi=bop_nominal_pressure_psi,
        fluid_density_kg_m3=fluid_density_kg_m3,
        lda_m=lda_m,
    )


def validate_pressure_high(
    t,
    p,
    designated_pressure,
    rwp,
    *,
    pressure_unit: str = "psi",
    high_test_justified_below_min: bool = False,
    bop_nominal_pressure_psi: float | None = None,
    fluid_density_kg_m3: float | None = None,
    lda_m: float | None = None,
    require_rwp_stabilization_rule: bool = False,
):
    spec = PressureTestSpec(mode="high")
    if require_rwp_stabilization_rule:
        spec = PressureTestSpec(mode="high", require_rwp_stabilization_rule=True)

    return evaluate_pressure_test(
        t,
        p,
        spec,
        designated_pressure_psi=designated_pressure,
        rwp_psi=rwp,
        pressure_unit=pressure_unit,
        high_test_justified_below_min=high_test_justified_below_min,
        bop_nominal_pressure_psi=bop_nominal_pressure_psi,
        fluid_density_kg_m3=fluid_density_kg_m3,
        lda_m=lda_m,
    )


def validate_soak(t, acc_pressure, pump_start, *, pump_stop: float | None = None):
    return evaluate_soak_test(t, acc_pressure, pump_start, pump_stop_psi=pump_stop)


def validate_function_test(records, *, regulator_records=None):
    return evaluate_closing_times(records, regulator_records=regulator_records)
