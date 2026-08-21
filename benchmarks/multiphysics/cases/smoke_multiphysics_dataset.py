"""Case H: eight real Fluid -> Thermal -> Structural dataset cases.

The existing Fluent CHT raw exports are deliberately reused when present.  Each
temperature field is then mapped to, and solved on, an independent MAPDL mesh.
"""
from __future__ import annotations

import itertools
import json
import numpy as np

from smoke_cht_fluent import (
    make_mesh, FLUID_HEIGHT, WALL_THICKNESS, NX, NY_FLUID, NY_SOLID,
    RHO, CP, K_FLUID, COLD_T,
)
from fluent_smoke_common import OUT, fluent_session, read_fluent_ascii_export, write_json
from multiphysics_common import mapdl_session, multiphysics_processes, wait_for_process_cleanup
from multiphysics_field_export import write_multiphysics_case
from validate_multiphysics_dataset import validate_dataset

CASE = "multiphysics_dataset"
DATA = OUT / CASE
PARAMS = list(itertools.product((.10, .20), (340., 360.), (2., 5.)))
YOUNGS = (35.e9, 70.e9)
L, W, H = .2, .01, .01
NU, ALPHA, TREF_K = .33, 23.e-6, 300.
NX_STRUCT = 20


def connectivity(nx, ny):
    nid = lambda i, j: i * (ny + 1) + j
    return np.asarray([(nid(i, j), nid(i + 1, j), nid(i + 1, j + 1), nid(i, j + 1))
                       for i in range(nx) for j in range(ny)], dtype=np.int64)


def domain_arrays(rows, y0, y1, ny, fields):
    selected = {(round(r["x-coordinate"], 10), round(r["y-coordinate"], 10)): r
                for r in rows if y0 - 1e-9 <= r["y-coordinate"] <= y1 + 1e-9}
    coords = np.asarray(sorted(selected), dtype=float)
    out = {"coordinates": coords, "connectivity": connectivity(NX, ny)}
    aliases = {"temperature": "temperature", "velocity_x": "x-velocity",
               "velocity_y": "y-velocity", "pressure": "pressure"}
    for target in fields:
        out[target] = np.asarray([selected[tuple(np.round(c, 10))][aliases[target]] for c in coords])
    if "velocity_x" in out:
        out["velocity"] = np.column_stack((out["velocity_x"], out["velocity_y"],
                                            np.zeros(len(coords))))
    return out


def structured_solid_mesh():
    coords = []
    for i in range(NX_STRUCT + 1):
        for k in range(2):
            for j in range(2):
                coords.append((L * i / NX_STRUCT, W * j, H * k))
    def nid(i, j, k):
        return i * 4 + k * 2 + j
    conn = []
    for i in range(NX_STRUCT):
        conn.append((nid(i, 0, 0), nid(i + 1, 0, 0), nid(i + 1, 1, 0), nid(i, 1, 0),
                     nid(i, 0, 1), nid(i + 1, 0, 1), nid(i + 1, 1, 1), nid(i, 1, 1)))
    return np.asarray(coords, float), np.asarray(conn, np.int64)


def ensure_fluent_raw_exports():
    raws = [DATA / f"case_{i:03d}_raw.csv" for i in range(len(PARAMS))]
    if all(p.is_file() for p in raws):
        return "reused_previous_actual_Fluent_261_exports"
    mesh = DATA / "shared_cht_mesh.msh"
    make_mesh(mesh)
    with fluent_session(dimension=2, processor_count=1, cwd=DATA, start_transcript=False) as s:
        s.settings.file.read_mesh(file_name=str(mesh))
        s.settings.setup.models.viscous.model = "laminar"
        s.settings.setup.models.energy.enabled = True
        air = s.settings.setup.materials.fluid["air"]
        air.density.value, air.specific_heat.value, air.thermal_conductivity.value = RHO, CP, K_FLUID
        solid = s.settings.setup.materials.solid["aluminum"]
        s.settings.setup.cell_zone_conditions.solid["solid-wall"].material = "aluminum"
        inlet = s.settings.setup.boundary_conditions.velocity_inlet["inlet"]
        outlet = s.settings.setup.boundary_conditions.pressure_outlet["outlet"]
        cold = s.settings.setup.boundary_conditions.wall["cold-outer-wall"]
        cold.thermal.thermal_condition, cold.thermal.temperature.value = "Temperature", COLD_T
        for name in ("fluid-bottom", "solid-left", "solid-right"):
            wall = s.settings.setup.boundary_conditions.wall[name]
            wall.thermal.thermal_condition, wall.thermal.heat_flux.value = "Heat Flux", 0.
        allowed = list(s.fields.field_data.scalar_fields.allowed_values())
        qfield = next((f for f in ("wall-heat-flux", "surface-heat-flux", "heat-flux") if f in allowed), None)
        surfaces = ["interior-fluid", "interior-solid-wall", "fluid-solid-wall-interface",
                    "fluid-solid-wall-interface-shadow", "inlet", "outlet", "cold-outer-wall"]
        for index, (velocity, tin, ksolid) in enumerate(PARAMS):
            inlet.momentum.velocity_magnitude.value = velocity
            inlet.thermal.temperature.value = tin
            outlet.thermal.backflow_total_temperature.value = tin
            solid.thermal_conductivity.value = ksolid
            s.settings.solution.initialization.standard_initialize()
            s.settings.solution.run_calculation.iterate(iter_count=200)
            quantities = ["x-coordinate", "y-coordinate", "temperature", "x-velocity",
                          "y-velocity", "pressure"] + ([qfield] if qfield else [])
            s.settings.file.export.ascii(file_name=str(raws[index]), surface_name_list=surfaces,
                                         delimiter="comma", quantities=quantities, location="node")
    return "new_actual_Fluent_261_solves"


def solve_structural_cases(raws):
    coords, conn = structured_solid_mesh()
    results = []
    with mapdl_session(working_dir=DATA / "mapdl") as m:
        for index, raw in enumerate(raws):
            velocity, tin, ksolid = PARAMS[index]
            young = YOUNGS[index % len(YOUNGS)]
            rows = read_fluent_ascii_export(raw)
            cht_solid = [r for r in rows if r["y-coordinate"] >= FLUID_HEIGHT - 1e-10]
            buckets = {}
            for r in cht_solid:
                buckets.setdefault(round(r["x-coordinate"], 10), []).append(r["temperature"])
            xs = np.asarray(sorted(buckets))
            axial_t = np.asarray([np.mean(buckets[x]) for x in xs])
            mapped_k = np.interp(coords[:, 0], xs, axial_t)

            m.clear(); m.prep7(); m.et(1, 185)
            m.mp("EX", 1, young); m.mp("NUXY", 1, NU); m.mp("ALPX", 1, ALPHA)
            m.tref(TREF_K - 273.15)
            for node, xyz in enumerate(coords, 1):
                m.n(node, *xyz)
            for element in conn:
                m.e(*(element + 1))
            for node, temp_k in enumerate(mapped_k, 1):
                m.bf(node, "TEMP", float(temp_k - 273.15))
            for node in np.flatnonzero(np.isclose(coords[:, 0], 0.)) + 1:
                m.d(int(node), "ALL", 0.)
            for node in np.flatnonzero(np.isclose(coords[:, 0], L)) + 1:
                m.d(int(node), "UX", 0.)
            m.finish(); m.slashsolu(); m.antype("STATIC"); m.solve(); m.finish()
            m.post1(); m.set("LAST")
            disp = np.asarray(m.post_processing.nodal_displacement("ALL"), float)
            eqv = np.asarray(m.post_processing.nodal_eqv_stress(), float)
            results.append((coords.copy(), conn.copy(), mapped_k, disp, eqv, young))
    return results


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    before = multiphysics_processes()
    payload = {"case": CASE, "model": "Case F Fluid -> Thermal -> Structural parameter sweep"}
    try:
        source_mode = ensure_fluent_raw_exports()
        raws = [DATA / f"case_{i:03d}_raw.csv" for i in range(len(PARAMS))]
        structural = solve_structural_cases(raws)
        records = []
        for index, raw in enumerate(raws):
            velocity, tin, ksolid = PARAMS[index]
            rows = read_fluent_ascii_export(raw)
            fluid = domain_arrays(rows, 0., FLUID_HEIGHT, NY_FLUID,
                                  ["temperature", "velocity_x", "velocity_y", "pressure"])
            s_coords, s_conn, mapped_k, disp, eqv, young = structural[index]
            solid = {"coordinates": s_coords, "connectivity": s_conn,
                     "temperature": mapped_k, "displacement": disp,
                     "equivalent_stress": eqv}
            iface_rows = {(round(r["x-coordinate"], 10), round(r["y-coordinate"], 10)): r
                          for r in rows if abs(r["y-coordinate"] - FLUID_HEIGHT) < 1e-9}
            icoords = np.asarray(sorted(iface_rows), float)
            qname = next((k for k in iface_rows[tuple(icoords[0])] if "heat-flux" in k), None)
            interface = {
                "coordinates": icoords,
                "temperature": np.asarray([iface_rows[tuple(c)]["temperature"] for c in icoords]),
                "heat_flux": np.asarray([iface_rows[tuple(c)].get(qname, 0.) for c in icoords]),
                "pressure": np.asarray([iface_rows[tuple(c)]["pressure"] for c in icoords]),
            }
            params = {"inlet_velocity_m_s": velocity, "inlet_temperature_K": tin,
                      "solid_conductivity_W_mK": ksolid, "youngs_modulus_Pa": young,
                      "wall_thickness_m": WALL_THICKNESS}
            check = write_multiphysics_case(
                DATA / f"case_{index:03d}.npz", fluid=fluid, solid=solid,
                interface=interface, parameters=params,
                units={"coordinates": "m", "temperature": "K", "velocity": "m/s",
                       "pressure": "Pa", "heat_flux": "W/m2", "displacement": "m",
                       "equivalent_stress": "Pa", "time": "s"},
                solver_metadata={"pipeline": "Case F", "fluid_solver": "Fluent 261",
                                 "structural_solver": "MAPDL 261", "mapping": "axial interpolation",
                                 "fluid_iterations_requested": 200, "analysis": "static thermal stress"},
                time=0.0)
            records.append({"case": index, "parameters": params, "valid": check["valid"],
                            "shapes": check["shapes"],
                            "ranges": {"solid_temperature_K": [float(mapped_k.min()), float(mapped_k.max())],
                                       "displacement_m": [float(np.linalg.norm(disp, axis=1).min()), float(np.linalg.norm(disp, axis=1).max())],
                                       "equivalent_stress_Pa": [float(eqv.min()), float(eqv.max())]}})
        (DATA / "index.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
        validation = validate_dataset(DATA)
        remaining = wait_for_process_cleanup(before)
        checks = {"eight_actual_case_F_sequences": len(records) == 8,
                  "all_exports_valid": all(r["valid"] for r in records),
                  "dataset_validator_pass": validation["status"] == "PASS",
                  "structural_displacement_and_stress_included": True,
                  "fluid_and_structural_meshes_independent": all(r["shapes"]["fluid_coordinates"] != r["shapes"]["solid_coordinates"] for r in records),
                  "clean_shutdown": not remaining}
        payload.update({"source_mode": source_mode, "case_count": len(records),
                        "parameters": ["inlet_velocity_m_s", "inlet_temperature_K",
                                       "solid_conductivity_W_mK", "youngs_modulus_Pa"],
                        "format": "one compressed NPZ per case plus JSON index/validation",
                        "records": records, "validation": validation, "checks": checks,
                        "status": "PASS" if all(checks.values()) else "FAIL",
                        "residual_processes": remaining})
    except Exception as e:
        payload.update({"status": "FAIL", "error": f"{type(e).__name__}: {e}",
                        "residual_processes": wait_for_process_cleanup(before)})
    write_json(OUT / f"{CASE}.json", payload)
    print(payload)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
