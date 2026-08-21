"""Solver-independent energy accounting for the reactive CHT benchmark."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from itertools import pairwise
from typing import Any


class EnergyAccountingError(ValueError):
    """Raised when an energy balance input is missing or physically ambiguous."""


def _finite(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EnergyAccountingError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise EnergyAccountingError(f"{name} must be a finite number")
    return result


def compute_energy_balance(
    *,
    mass_flow_in: float,
    inlet_total_enthalpy: float,
    mass_flow_out: float,
    outlet_total_enthalpy: float,
    wall_heat_out: float,
    stored_energy_before: float,
    stored_energy_after: float,
    duration: float,
    threshold: float = 0.10,
) -> dict[str, float | bool]:
    """Apply ``dE/dt = H_in - H_out - Q_wall,out`` for a unit-depth 2-D model.

    Mass flow is in kg/s/m, specific enthalpy in J/kg, wall heat in W/m,
    stored energy in J/m, and duration in seconds. Inputs use explicit positive
    magnitudes for flow entering/leaving the control volume and heat leaving it.
    """
    values = {
        "mass_flow_in": _finite("mass_flow_in", mass_flow_in),
        "inlet_total_enthalpy": _finite("inlet_total_enthalpy", inlet_total_enthalpy),
        "mass_flow_out": _finite("mass_flow_out", mass_flow_out),
        "outlet_total_enthalpy": _finite("outlet_total_enthalpy", outlet_total_enthalpy),
        "wall_heat_out": _finite("wall_heat_out", wall_heat_out),
        "stored_energy_before": _finite("stored_energy_before", stored_energy_before),
        "stored_energy_after": _finite("stored_energy_after", stored_energy_after),
        "duration": _finite("duration", duration),
        "threshold": _finite("threshold", threshold),
    }
    if values["mass_flow_in"] < 0 or values["mass_flow_out"] < 0:
        raise EnergyAccountingError("mass-flow magnitudes must be nonnegative")
    if values["wall_heat_out"] < 0:
        raise EnergyAccountingError("wall_heat_out must use a nonnegative outward-positive convention")
    if values["duration"] <= 0:
        raise EnergyAccountingError("duration must be positive")
    if not 0 <= values["threshold"] < 1:
        raise EnergyAccountingError("threshold must be in [0, 1)")

    enthalpy_in = values["mass_flow_in"] * values["inlet_total_enthalpy"]
    enthalpy_out = values["mass_flow_out"] * values["outlet_total_enthalpy"]
    advective_net_in = enthalpy_in - enthalpy_out
    accumulation = (values["stored_energy_after"] - values["stored_energy_before"]) / values["duration"]
    residual = advective_net_in - values["wall_heat_out"] - accumulation
    scale = max(abs(advective_net_in), abs(values["wall_heat_out"]) + abs(accumulation), 1e-30)
    relative_error = abs(residual) / scale
    return {
        "enthalpy_in_W_per_m": enthalpy_in,
        "enthalpy_out_W_per_m": enthalpy_out,
        "advective_enthalpy_net_in_W_per_m": advective_net_in,
        "wall_heat_out_W_per_m": values["wall_heat_out"],
        "accumulation_W_per_m": accumulation,
        "residual_W_per_m": residual,
        "normalization_W_per_m": scale,
        "relative_error": relative_error,
        "threshold": values["threshold"],
        "passes": relative_error < values["threshold"],
    }


def _trapezoidal_mean(values: Sequence[float]) -> float:
    if len(values) < 2:
        raise EnergyAccountingError("a window requires at least two samples")
    return (0.5 * values[0] + sum(values[1:-1]) + 0.5 * values[-1]) / (len(values) - 1)


def compute_windowed_energy_balance(
    samples: Sequence[Mapping[str, Any]], *, time_step: float, threshold: float = 0.10
) -> dict[str, float | int | bool]:
    """Balance a fixed equally spaced window using matched trapezoidal flux averages."""
    if len(samples) < 2:
        raise EnergyAccountingError("a window requires at least two samples")
    dt = _finite("time_step", time_step)
    if dt <= 0:
        raise EnergyAccountingError("time_step must be positive")

    required = (
        "mass_flow_in",
        "inlet_total_enthalpy",
        "mass_flow_out",
        "outlet_total_enthalpy",
        "wall_heat_out",
        "stored_energy",
    )
    normalized: list[dict[str, float]] = []
    for index, sample in enumerate(samples):
        missing = [name for name in required if name not in sample]
        if missing:
            raise EnergyAccountingError(f"sample {index} missing {missing}")
        normalized.append({name: _finite(f"sample {index} {name}", sample[name]) for name in required})

    for sample in normalized:
        if sample["mass_flow_in"] < 0 or sample["mass_flow_out"] < 0 or sample["wall_heat_out"] < 0:
            raise EnergyAccountingError("window samples must use nonnegative outward-positive magnitudes")
    enthalpy_in = [sample["mass_flow_in"] * sample["inlet_total_enthalpy"] for sample in normalized]
    enthalpy_out = [sample["mass_flow_out"] * sample["outlet_total_enthalpy"] for sample in normalized]
    duration = (len(normalized) - 1) * dt
    balance = compute_energy_balance(
        mass_flow_in=1.0,
        inlet_total_enthalpy=_trapezoidal_mean(enthalpy_in),
        mass_flow_out=1.0,
        outlet_total_enthalpy=_trapezoidal_mean(enthalpy_out),
        wall_heat_out=_trapezoidal_mean([sample["wall_heat_out"] for sample in normalized]),
        stored_energy_before=normalized[0]["stored_energy"],
        stored_energy_after=normalized[-1]["stored_energy"],
        duration=duration,
        threshold=threshold,
    )
    balance.update({"sample_count": len(normalized), "interval_count": len(normalized) - 1, "duration_s": duration})
    return balance


def surface_heat_consistency(*, native_heat_out: float, exported_heat_out: float) -> dict[str, float]:
    """Compare native and exported wall integrations using outward-positive values."""
    native = _finite("native_heat_out", native_heat_out)
    exported = _finite("exported_heat_out", exported_heat_out)
    if native < 0 or exported < 0:
        raise EnergyAccountingError("surface heat values must be outward-positive")
    difference = exported - native
    return {
        "native_heat_out_W_per_m": native,
        "exported_heat_out_W_per_m": exported,
        "difference_W_per_m": difference,
        "relative_difference": abs(difference) / max(abs(native), 1e-30),
    }


def trapezoidal_integral(values: Sequence[float], coordinates: Sequence[float]) -> float:
    """Integrate paired samples without requiring a NumPy-version-specific API."""
    if len(values) != len(coordinates) or len(values) < 2:
        raise EnergyAccountingError("trapezoidal integration requires equal-length arrays with at least two points")
    y = [_finite(f"value {index}", value) for index, value in enumerate(values)]
    x = [_finite(f"coordinate {index}", value) for index, value in enumerate(coordinates)]
    if any(right <= left for left, right in pairwise(x)):
        raise EnergyAccountingError("trapezoidal coordinates must be strictly increasing")
    return sum(0.5 * (left_y + right_y) * (right_x - left_x) for left_y, right_y, left_x, right_x in zip(
        y[:-1], y[1:], x[:-1], x[1:], strict=True
    ))
