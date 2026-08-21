import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "benchmarks" / "phase_reactive" / "common" / "energy_accounting.py"
SPEC = importlib.util.spec_from_file_location("case_j_energy_accounting", MODULE_PATH)
assert SPEC and SPEC.loader
energy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(energy)


def test_known_conservative_balance_passes():
    result = energy.compute_energy_balance(
        mass_flow_in=2.0,
        inlet_total_enthalpy=10.0,
        mass_flow_out=1.0,
        outlet_total_enthalpy=8.0,
        wall_heat_out=5.0,
        stored_energy_before=100.0,
        stored_energy_after=107.0,
        duration=1.0,
    )
    assert result["residual_W_per_m"] == pytest.approx(0.0)
    assert result["passes"] is True


def test_sign_error_is_rejected():
    with pytest.raises(energy.EnergyAccountingError, match="outward-positive"):
        energy.compute_energy_balance(
            mass_flow_in=1.0,
            inlet_total_enthalpy=10.0,
            mass_flow_out=1.0,
            outlet_total_enthalpy=8.0,
            wall_heat_out=-2.0,
            stored_energy_before=1.0,
            stored_energy_after=1.0,
            duration=1.0,
        )


def test_missing_window_quantity_is_invalid():
    sample = {
        "mass_flow_in": 1.0,
        "inlet_total_enthalpy": 10.0,
        "mass_flow_out": 1.0,
        "outlet_total_enthalpy": 8.0,
        "wall_heat_out": 2.0,
    }
    with pytest.raises(energy.EnergyAccountingError, match="stored_energy"):
        energy.compute_windowed_energy_balance([sample, sample], time_step=0.1)


def test_threshold_boundary_is_deterministic_and_strict():
    result = energy.compute_energy_balance(
        mass_flow_in=1.0,
        inlet_total_enthalpy=10.0,
        mass_flow_out=1.0,
        outlet_total_enthalpy=0.0,
        wall_heat_out=9.0,
        stored_energy_before=0.0,
        stored_energy_after=0.0,
        duration=1.0,
        threshold=0.10,
    )
    assert result["relative_error"] == pytest.approx(0.10)
    assert result["passes"] is False


def test_window_uses_matching_trapezoidal_flux_average():
    samples = [
        {
            "mass_flow_in": 1.0,
            "inlet_total_enthalpy": inlet,
            "mass_flow_out": 1.0,
            "outlet_total_enthalpy": 0.0,
            "wall_heat_out": 2.0,
            "stored_energy": stored,
        }
        for inlet, stored in ((4.0, 10.0), (6.0, 13.0), (8.0, 18.0))
    ]
    result = energy.compute_windowed_energy_balance(samples, time_step=1.0)
    assert result["advective_enthalpy_net_in_W_per_m"] == pytest.approx(6.0)
    assert result["accumulation_W_per_m"] == pytest.approx(4.0)
    assert result["residual_W_per_m"] == pytest.approx(0.0)
    assert result["passes"] is True


def test_historical_case_j_recomputes_published_failure():
    result = energy.compute_energy_balance(
        mass_flow_in=0.0001347178728035387,
        inlet_total_enthalpy=549937.2506496907,
        mass_flow_out=0.0001347178754009,
        outlet_total_enthalpy=404037.6560185514,
        wall_heat_out=27.66941152545065,
        stored_energy_before=42787.501267164145,
        stored_energy_after=42787.48574088186,
        duration=0.005,
    )
    assert result["residual_W_per_m"] == pytest.approx(-4.908873085638277)
    assert result["relative_error"] == pytest.approx(0.1595101883255324)
    assert result["passes"] is False


def test_trapezoidal_integration_is_numpy_version_independent():
    assert energy.trapezoidal_integral([0.0, 2.0, 2.0], [0.0, 1.0, 3.0]) == pytest.approx(5.0)
    with pytest.raises(energy.EnergyAccountingError, match="strictly increasing"):
        energy.trapezoidal_integral([0.0, 1.0], [1.0, 1.0])
