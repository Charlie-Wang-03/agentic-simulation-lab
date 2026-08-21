"""Case D: regularized moving-source melt-pool trend benchmark."""

from __future__ import annotations

import json
import numpy as np

from phase_reactive_common import (OUT, base_payload, ensure_dirs, gaussian_moving_temperature,
                                   liquid_fraction, structured_quad_mesh, write_json)


CASE = "D"


def run(power: float, speed: float) -> dict:
    xs = np.linspace(0.0, 0.020, 161); ys = np.linspace(-0.004, 0.004, 81)
    coords, conn = structured_quad_mesh(xs, ys)
    temp = gaussian_moving_temperature(coords[:, 0], coords[:, 1], power=power, speed=speed,
        absorptivity=0.35, conductivity=24.0, ambient_temperature=300.0,
        source_x=0.012, beam_radius=0.0005)
    frac = liquid_fraction(temp, 1650.0, 1700.0)
    molten = coords[frac > 0.5]
    length = float(np.ptp(molten[:, 0])) if len(molten) else 0.0
    width = float(np.ptp(molten[:, 1])) if len(molten) else 0.0
    return {"coordinates": coords, "connectivity": conn, "temperature": temp,
            "liquid_fraction": frac, "melt_pool_length_m": length,
            "melt_pool_width_m": width, "power_W": power, "scan_speed_m_s": speed}


def main() -> int:
    ensure_dirs()
    settings = [(1800.0, 0.20), (2400.0, 0.20), (2400.0, 0.40)]
    results = [run(*p) for p in settings]
    files = []
    for i, r in enumerate(results):
        path = OUT / f"case_d_{i:02d}.npz"
        meta = {"case": CASE, "model": "regularized Rosenthal-like moving source",
                "parameters": {"power_W": r["power_W"], "scan_speed_m_s": r["scan_speed_m_s"]},
                "units": {"coordinates": "m", "temperature": "K", "liquid_fraction": "1"}}
        np.savez_compressed(path, coordinates=r["coordinates"], connectivity=r["connectivity"],
                            temperature=r["temperature"], liquid_fraction=r["liquid_fraction"],
                            metadata_json=np.asarray(json.dumps(meta)))
        files.append(str(path.resolve()))
    low, high, fast = results
    checks = {"liquid_fraction_bounded": all(bool(((r["liquid_fraction"] >= 0) & (r["liquid_fraction"] <= 1)).all()) for r in results),
              "higher_power_larger_pool": high["melt_pool_length_m"] > low["melt_pool_length_m"] and high["melt_pool_width_m"] > low["melt_pool_width_m"],
              "higher_speed_smaller_pool": fast["melt_pool_length_m"] < high["melt_pool_length_m"] and fast["melt_pool_width_m"] <= high["melt_pool_width_m"],
              "temperature_finite": all(np.isfinite(r["temperature"]).all() for r in results)}
    summaries = [{k: r[k] for k in ("power_W", "scan_speed_m_s", "melt_pool_length_m", "melt_pool_width_m")} for r in results]
    payload = base_payload(CASE, "Moving Gaussian heat-source melt-pool trend", "reduced-order Rosenthal-like benchmark")
    payload.update({"model_scope": "independent trend benchmark; not reported as Fluent",
                    "results": summaries, "checks": checks, "files": files,
                    "status": "PASS" if all(checks.values()) else "FAIL"})
    write_json(OUT / "case_d.json", payload); print(payload)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
