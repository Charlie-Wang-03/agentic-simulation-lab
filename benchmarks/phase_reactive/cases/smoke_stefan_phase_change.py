"""Case A: one-phase Stefan latent-heat benchmark with energy accounting."""

from __future__ import annotations

import math
import numpy as np
from scipy.optimize import brentq
from scipy.special import erf

from phase_reactive_common import OUT, base_payload, ensure_dirs, relative_error, write_json


CASE = "A"


def main() -> int:
    ensure_dirs()
    rho, cp, conductivity, latent = 780.0, 2200.0, 0.20, 180_000.0
    tm, th = 300.0, 340.0
    alpha = conductivity / (rho * cp)
    ste = cp * (th - tm) / latent
    equation = lambda lam: math.sqrt(math.pi) * lam * math.exp(lam * lam) * erf(lam) - ste
    lam = brentq(equation, 1e-10, 3.0)
    times = np.asarray([60.0, 300.0, 900.0, 1800.0, 3600.0])
    x = np.linspace(0.0, 0.08, 801)
    temperatures, fractions, interfaces, total_h = [], [], [], []
    energy_errors = []
    for t in times:
        front = 2.0 * lam * math.sqrt(alpha * t)
        temp = np.full_like(x, tm)
        mask = x <= front
        temp[mask] = th - (th - tm) * np.asarray([erf(v / (2 * math.sqrt(alpha * t))) for v in x[mask]]) / erf(lam)
        frac = (x < front).astype(float)
        sensible = rho * np.trapezoid(cp * (temp - tm), x)
        latent_energy = rho * latent * front
        input_heat = 2 * conductivity * (th - tm) * math.sqrt(t) / (erf(lam) * math.sqrt(math.pi * alpha))
        balance = sensible + latent_energy
        energy_errors.append(relative_error(balance, input_heat))
        temperatures.append(temp); fractions.append(frac); interfaces.append(front); total_h.append(balance)
    temperatures = np.stack(temperatures); fractions = np.stack(fractions)
    npz = OUT / "case_a_stefan_phase_change.npz"
    metadata = {
        "case": CASE, "model": "one-phase Stefan analytical solution", "units": {
            "x": "m", "time": "s", "temperature": "K", "liquid_fraction": "1",
            "interface_position": "m", "total_enthalpy_per_area": "J/m2"},
        "material": {"density_kg_m3": rho, "specific_heat_J_kgK": cp,
                     "conductivity_W_mK": conductivity, "melting_temperature_K": tm,
                     "latent_heat_J_kg": latent},
    }
    np.savez_compressed(npz, coordinates=x[:, None], time=times, temperature=temperatures,
                        liquid_fraction=fractions, interface_position=np.asarray(interfaces),
                        total_enthalpy_per_area=np.asarray(total_h), metadata_json=np.asarray(__import__('json').dumps(metadata)))
    checks = {
        "stefan_root_residual_lt_1e-10": abs(equation(lam)) < 1e-10,
        "interface_monotonic": bool(np.all(np.diff(interfaces) > 0)),
        "interface_sqrt_time": bool(np.allclose(np.asarray(interfaces) / np.sqrt(times), interfaces[0] / math.sqrt(times[0]))),
        "liquid_fraction_bounded": bool(((fractions >= 0) & (fractions <= 1)).all()),
        "max_energy_error_lt_0p5pct": max(energy_errors) < 0.005,
    }
    payload = base_payload(CASE, "One-dimensional latent-heat Stefan benchmark", "SciPy analytical reference")
    payload.update({"model": metadata, "results": {"Ste": ste, "lambda": lam,
                    "interface_position_m": interfaces, "max_energy_relative_error": max(energy_errors)},
                    "checks": checks, "files": [str(npz.resolve())],
                    "status": "PASS" if all(checks.values()) else "FAIL"})
    write_json(OUT / "case_a.json", payload)
    print(payload)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
