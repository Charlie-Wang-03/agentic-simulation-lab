"""NPZ + JSON field export helpers for frequency- and time-domain acoustics."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def _finite(name: str, values: np.ndarray) -> np.ndarray:
    values = np.asarray(values)
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{name} contains NaN or Inf")
    return values


def export_frequency_domain(
    npz_path: Path,
    metadata_path: Path,
    *,
    coordinates: np.ndarray,
    connectivity: np.ndarray,
    frequencies_hz: np.ndarray,
    pressure_real: np.ndarray,
    pressure_imag: np.ndarray,
    metadata: dict,
) -> None:
    coordinates = _finite("coordinates", coordinates).astype(float)
    connectivity = np.asarray(connectivity, dtype=np.int64)
    frequencies_hz = _finite("frequencies_hz", frequencies_hz).astype(float)
    pressure_real = _finite("pressure_real", pressure_real).astype(float)
    pressure_imag = _finite("pressure_imag", pressure_imag).astype(float)
    expected = (frequencies_hz.size, coordinates.shape[0])
    if pressure_real.shape != expected or pressure_imag.shape != expected:
        raise ValueError(f"pressure shape must be {expected}")
    pressure_amplitude = np.hypot(pressure_real, pressure_imag)
    pressure_phase = np.arctan2(pressure_imag, pressure_real)
    np.savez_compressed(npz_path, coordinates=coordinates, connectivity=connectivity, frequency=frequencies_hz, pressure_real=pressure_real, pressure_imag=pressure_imag, pressure_amplitude=pressure_amplitude, pressure_phase=pressure_phase)
    payload = {**metadata, "format": "NPZ", "domain": "frequency", "units": {"coordinates": "m", "frequency": "Hz", "pressure": "Pa", "pressure_phase": "rad"}, "shapes": {"coordinates": list(coordinates.shape), "connectivity": list(connectivity.shape), "pressure": list(expected)}, "npz_file": str(npz_path.resolve())}
    metadata_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def export_time_domain(npz_path: Path, metadata_path: Path, *, coordinates: np.ndarray, connectivity: np.ndarray, time_s: np.ndarray, pressure: np.ndarray, metadata: dict) -> None:
    coordinates = _finite("coordinates", coordinates).astype(float)
    connectivity = np.asarray(connectivity, dtype=np.int64)
    time_s = _finite("time_s", time_s).astype(float)
    pressure = _finite("pressure", pressure).astype(float)
    expected = (time_s.size, coordinates.shape[0])
    if pressure.shape != expected:
        raise ValueError(f"pressure shape must be {expected}")
    if np.any(np.diff(time_s) <= 0):
        raise ValueError("time must be strictly increasing")
    np.savez_compressed(npz_path, coordinates=coordinates, connectivity=connectivity, time=time_s, pressure=pressure)
    payload = {**metadata, "format": "NPZ", "domain": "time", "units": {"coordinates": "m", "time": "s", "pressure": "Pa"}, "shapes": {"coordinates": list(coordinates.shape), "connectivity": list(connectivity.shape), "pressure": list(expected)}, "npz_file": str(npz_path.resolve())}
    metadata_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
