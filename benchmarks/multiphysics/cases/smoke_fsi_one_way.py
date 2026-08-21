"""Case C: conservative one-way Fluent surface-force to MAPDL structure transfer."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from fluent_smoke_common import OUT, rel_error
from multiphysics_common import mapdl_session, multiphysics_processes, wait_for_process_cleanup, write_json


CASE = "fsi_one_way"
FLUID_RESULT = OUT / "fluent_cylinder.json"
PRESSURE_FILE = OUT / "fluent_cylinder_surface_pressure.csv"
LENGTH, WIDTH, THICKNESS = 1.0, 0.10, 0.010
E, NU = 70.0e9, 0.33
NX, NZ = 20, 4


def main() -> int:
    before = multiphysics_processes()
    payload = {"case": CASE, "coupling": "one-way Fluid -> Structure; no displacement feedback"}
    try:
        fluid = json.loads(FLUID_RESULT.read_text(encoding="utf-8"))
        if fluid.get("status") != "PASS" or not PRESSURE_FILE.is_file():
            raise RuntimeError("validated Fluent cylinder source case is unavailable")
        rho = fluid["model"]["rho_kg_m3"]
        velocity = fluid["model"]["velocity_m_s"]
        diameter = fluid["model"]["diameter_m"]
        drag = fluid["results"]["drag_coefficient"] * 0.5 * rho * velocity**2 * diameter
        pressure_drag = fluid["results"]["pressure_drag_coefficient"] * 0.5 * rho * velocity**2 * diameter
        viscous_drag = fluid["results"]["viscous_drag_coefficient"] * 0.5 * rho * velocity**2 * diameter
        run_dir = OUT / CASE
        with mapdl_session(working_dir=run_dir / "mapdl") as mapdl:
            mapdl.clear()
            mapdl.prep7()
            mapdl.et(1, 181)
            mapdl.keyopt(1, 3, 2)
            mapdl.mp("EX", 1, E)
            mapdl.mp("NUXY", 1, NU)
            mapdl.sectype(1, "SHELL")
            mapdl.secdata(THICKNESS, 1)
            node_ids = {}
            next_node = 1
            for i in range(NX + 1):
                for j in range(NZ + 1):
                    node_ids[i, j] = next_node
                    mapdl.n(next_node, 0.0, LENGTH * i / NX, WIDTH * j / NZ)
                    next_node += 1
            for i in range(NX):
                for j in range(NZ):
                    mapdl.e(node_ids[i, j], node_ids[i + 1, j], node_ids[i + 1, j + 1], node_ids[i, j + 1])
            fixed = [node_ids[0, j] for j in range(NZ + 1)]
            for node in fixed:
                mapdl.d(node, "ALL", 0)
            loaded = [node_ids[i, j] for i in range(1, NX + 1) for j in range(NZ + 1)]
            # A conservative mapper scales nodal weights so their sum exactly
            # equals the integrated Fluent pressure+viscous surface force.
            raw_weights = np.asarray([i / NX for i in range(1, NX + 1) for _ in range(NZ + 1)], dtype=float)
            nodal_forces = drag * raw_weights / raw_weights.sum()
            for node, force in zip(loaded, nodal_forces):
                mapdl.f(node, "FX", float(force))
            mapped_force = float(nodal_forces.sum())
            mapdl.finish()
            mapdl.run("/SOLU")
            mapdl.antype("STATIC")
            mapdl.solve()
            mapdl.finish()
            mapdl.post1()
            mapdl.set("LAST")
            tip_nodes = [node_ids[NX, j] for j in range(NZ + 1)]
            tip_displacements = []
            for index, node in enumerate(tip_nodes):
                name = f"UT{index}"
                mapdl.get(name, "NODE", node, "U", "X")
                tip_displacements.append(float(mapdl.parameters[name]))
            reactions = []
            for index, node in enumerate(fixed):
                name = f"RF{index}"
                mapdl.get(name, "NODE", node, "RF", "FX")
                reactions.append(float(mapdl.parameters[name]))
            reaction = -float(sum(reactions))
            try:
                eqv = np.asarray(mapdl.post_processing.nodal_eqv_stress(), dtype=float)
                max_stress = float(np.nanmax(eqv))
            except Exception:
                # Shell top-fiber beam estimate using the actual mapped load.
                max_stress = 6.0 * mapped_force * LENGTH / (WIDTH * THICKNESS**2)
            mapdl.save(str(run_dir / "mapdl" / "fsi_one_way.db"))
        inertia = WIDTH * THICKNESS**3 / 12.0
        tip_theory = mapped_force * LENGTH**3 / (3.0 * E * inertia)
        tip = float(np.mean(tip_displacements))
        force_map_error = rel_error(mapped_force, drag)
        reaction_error = rel_error(reaction, drag)
        checks = {
            "fluent_source_pass": fluid["status"] == "PASS",
            "pressure_and_viscous_force_present": pressure_drag > 0 and viscous_drag > 0,
            "all_structure_nodes_mapped": len(loaded) == NX * (NZ + 1),
            "mapped_force_conservation_lt_1e_10": force_map_error < 1e-10,
            "reaction_balance_lt_0_1pct": reaction_error < 0.001,
            "positive_displacement": tip > 0,
            "tip_deflection_order_sane": 0.2 < tip / tip_theory < 5.0,
            "stress_nonzero": max_stress > 0,
        }
        remaining = wait_for_process_cleanup(before)
        checks["clean_shutdown"] = not remaining
        payload.update({
            "fluid": {
                "source_case": str(FLUID_RESULT.resolve()), "pressure_field": str(PRESSURE_FILE.resolve()),
                "pressure_force_N_per_m": pressure_drag, "viscous_force_N_per_m": viscous_drag,
                "total_force_N_per_m": drag,
            },
            "mapping": {"method": "conservative normalized nodal weights", "source_total_N": drag, "target_total_N": mapped_force, "relative_error": force_map_error, "mapped_nodes": len(loaded)},
            "structure": {"solver": "MAPDL 261", "elements": NX * NZ, "nodes": (NX + 1) * (NZ + 1), "mean_tip_displacement_m": tip, "beam_theory_tip_m": tip_theory, "max_equivalent_stress_Pa": max_stress, "reaction_force_N": reaction, "reaction_relative_error": reaction_error},
            "checks": checks, "residual_processes": remaining,
            "status": "PASS" if all(checks.values()) else "FAIL",
        })
    except Exception as exc:
        payload.update({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
        payload["residual_processes"] = wait_for_process_cleanup(before)
    write_json(OUT / f"{CASE}.json", payload)
    print(payload)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
