"""Case E: first-order A -> B plug-flow reaction benchmark."""

from __future__ import annotations

import json
import numpy as np

from phase_reactive_common import OUT, base_payload, ensure_dirs, first_order_plug_profile, write_json


CASE = "E"


def main() -> int:
    ensure_dirs()
    length, velocity, rate = 1.0, 0.2, 0.7
    x = np.linspace(0.0, length, 201)
    ya_exact, yb_exact = first_order_plug_profile(x, velocity=velocity, rate_constant=rate)
    dx = x[1] - x[0]
    ya_fv = np.empty_like(x); ya_fv[0] = 1.0
    for i in range(1, len(x)):
        ya_fv[i] = ya_fv[i - 1] / (1.0 + rate * dx / velocity)
    yb_fv = 1.0 - ya_fv
    reaction_rate = rate * ya_fv
    max_error = float(np.max(np.abs(ya_fv - ya_exact)))
    conversion = float(1.0 - ya_fv[-1])
    metadata = {"case": CASE, "reaction": "A -> B", "rate_law": "r=k*C_A",
                "species_names": ["A", "B"], "rate_constant_1_s": rate,
                "units": {"x": "m", "mass_fraction": "1", "reaction_rate": "1/s"}}
    npz = OUT / "case_e_reaction_diffusion.npz"
    np.savez_compressed(npz, coordinates=x[:, None], species_A=ya_fv, species_B=yb_fv,
                        reaction_rate=reaction_rate, analytical_A=ya_exact,
                        metadata_json=np.asarray(json.dumps(metadata)))
    checks = {"max_abs_analytical_error_lt_0p005": max_error < 0.005,
              "species_bounded": bool(((ya_fv >= 0) & (ya_fv <= 1) & (yb_fv >= 0) & (yb_fv <= 1)).all()),
              "species_sum_error_lt_1e-12": float(np.max(np.abs(ya_fv + yb_fv - 1))) < 1e-12,
              "conversion_physical": 0.9 < conversion < 1.0,
              "reaction_rate_finite": bool(np.isfinite(reaction_rate).all())}
    payload = base_payload(CASE, "First-order reaction-diffusion/plug-flow benchmark", "implicit upwind finite volume")
    payload.update({"model": metadata, "results": {"outlet_conversion": conversion,
                    "max_abs_error_vs_analytical": max_error}, "checks": checks,
                    "files": [str(npz.resolve())], "status": "PASS" if all(checks.values()) else "FAIL"})
    write_json(OUT / "case_e.json", payload); print(payload)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
