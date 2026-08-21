"""Generate ten genuinely solved Maxwell electrostatic samples and an NPZ dataset."""

from __future__ import annotations

import json
import math
import traceback

import numpy as np

from aedt_smoke_common import OUTPUT_ROOT, aedt_pid_set, aedt_processes, cleanup_new_aedt_processes, ensure_dirs, prepare_pyaedt_student_runtime, student_launch_kwargs, utc_now, write_json


def _read_scalar_field(path):
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[2:]:
        parts = line.split()
        if len(parts) >= 4:
            try:
                rows.append([float(parts[0]), float(parts[1]), float(parts[2]), float(parts[-1])])
            except ValueError:
                pass
    return np.asarray(rows, dtype=np.float64)


def _canonical(rows):
    order = np.lexsort((rows[:, 0], rows[:, 1], rows[:, 2]))
    return rows[order, :3], rows[order, 3]


def _quad_connectivity(nodes):
    xs = sorted(set(np.round(nodes[:, 0], 12)))
    ys = sorted(set(np.round(nodes[:, 1], 12)))
    index = {(round(x, 12), round(y, 12)): i for i, (x, y, _) in enumerate(nodes)}
    quads = []
    for y0, y1 in zip(ys[:-1], ys[1:]):
        for x0, x1 in zip(xs[:-1], xs[1:]):
            quads.append([index[(x0, y0)], index[(x1, y0)], index[(x1, y1)], index[(x0, y1)]])
    return np.asarray(quads, dtype=np.int32)


def main() -> int:
    ensure_dirs()
    out = OUTPUT_ROOT / "dataset_electrostatic_10"
    out.mkdir(parents=True, exist_ok=True)
    result = {"name": "Electrostatic voltage sweep dataset", "timestamp_utc": utc_now(), "status": "FAIL"}
    baseline = aedt_pid_set()
    app = None
    try:
        runtime = prepare_pyaedt_student_runtime()
        result["runtime"] = runtime
        from ansys.aedt.core import Maxwell2d

        app = Maxwell2d(project="Dataset_Electrostatic", design="VoltageSweep", solution_type="Electrostatic", **student_launch_kwargs(runtime))
        app.modeler.model_units = "mm"
        lower = app.modeler.create_rectangle([-50, -6, 0], [100, 1], name="LowerPlate", material="copper")
        upper = app.modeler.create_rectangle([-50, 5, 0], [100, 1], name="UpperPlate", material="copper")
        region = app.modeler.create_region([100, 500, 100, 100], name="AirRegion")
        app.model_depth = "100mm"
        app.assign_voltage([lower.name], amplitude="0V", name="Ground")
        signal = app.assign_voltage([upper.name], amplitude="1V", name="Signal")
        app.assign_balloon(region.edges, boundary="OuterBoundary")
        app.mesh.assign_length_mesh([upper.name, lower.name], inside_selection=True, maximum_length="3mm", name="PlateMesh")
        setup = app.create_setup("Setup1", MaximumPasses=1, PercentError=5.0)
        voltages = np.asarray([0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0], dtype=np.float64)
        e_fields, potentials, samples = [], [], []
        nodes_ref = None
        for index, voltage in enumerate(voltages):
            signal.props["Value"] = f"{voltage:g}V"
            signal.update()
            solved = bool(app.analyze(setup=setup.name, cores=2, use_auto_settings=False))
            sample_dir = out / f"sample_{index:02d}"
            sample_dir.mkdir(parents=True, exist_ok=True)
            e_file = sample_dir / "Mag_E.fld"
            v_file = sample_dir / "Voltage.fld"
            e_export = app.post.export_field_file_on_grid("Mag_E", solution="Setup1 : LastAdaptive", file_name=str(e_file), grid_start=[-40, -4, 0], grid_stop=[40, 4, 0], grid_step=[10, 1, 1], export_in_si_system=True)
            v_export = app.post.export_field_file_on_grid("Voltage", solution="Setup1 : LastAdaptive", file_name=str(v_file), grid_start=[-40, -4, 0], grid_stop=[40, 4, 0], grid_step=[10, 1, 1], export_in_si_system=True)
            nodes_e, values_e = _canonical(_read_scalar_field(e_file))
            nodes_v, values_v = _canonical(_read_scalar_field(v_file))
            same_nodes = nodes_e.shape == nodes_v.shape and np.allclose(nodes_e, nodes_v, rtol=0, atol=1e-12)
            if nodes_ref is None:
                nodes_ref = nodes_e
            stable_nodes = nodes_ref.shape == nodes_e.shape and np.allclose(nodes_ref, nodes_e, rtol=0, atol=1e-12)
            e_fields.append(values_e)
            potentials.append(values_v)
            messages = list(app.odesktop.GetMessages(app.project_name, app.design_name, 0))
            normal_completion = any("Normal completion" in m for m in messages)
            samples.append({"index": index, "voltage_V": float(voltage), "solved": solved, "normal_completion": normal_completion, "node_count": int(len(nodes_e)), "mean_E_V_per_m": float(np.mean(values_e)), "max_E_V_per_m": float(np.max(values_e)), "potential_min_V": float(np.min(values_v)), "potential_max_V": float(np.max(values_v)), "same_E_V_nodes": same_nodes, "stable_nodes": stable_nodes, "files": {"Mag_E": str(e_export), "Voltage": str(v_export)}})
        connectivity = _quad_connectivity(nodes_ref)
        e_array = np.stack(e_fields)
        v_array = np.stack(potentials)
        labels = np.column_stack((e_array.mean(axis=1), e_array.max(axis=1)))
        npz_file = out / "electrostatic_voltage_sweep.npz"
        np.savez_compressed(npz_file, nodes_m=nodes_ref, connectivity_quads=connectivity, parameters_voltage_V=voltages[:, None], field_E_magnitude_V_per_m=e_array, field_potential_V=v_array, labels_mean_max_E_V_per_m=labels)
        project_file = out / "electrostatic_voltage_sweep.aedt"
        saved = bool(app.save_project(project_file))
        checks = {"ten_samples": len(samples) == 10, "all_solved": all(s["solved"] and s["normal_completion"] for s in samples), "all_fields_same_nodes": all(s["same_E_V_nodes"] and s["stable_nodes"] for s in samples), "finite_arrays": all(np.isfinite(a).all() for a in (nodes_ref, connectivity, voltages, e_array, v_array, labels)), "nonempty_connectivity": connectivity.shape[0] > 0, "project_saved": saved, "npz_exists": npz_file.exists()}
        result.update({"status": "PASS" if all(checks.values()) else "FAIL", "sample_count": len(samples), "samples": samples, "dataset": {"npz": str(npz_file), "nodes": {"array": "nodes_m", "shape": list(nodes_ref.shape), "description": "coordinates of the exported structured sampling mesh in SI metres"}, "connectivity": {"array": "connectivity_quads", "shape": list(connectivity.shape), "index_base": 0, "description": "quad connectivity of the exported sampling mesh; not the proprietary adaptive FEM mesh"}, "parameters": {"array": "parameters_voltage_V", "shape": [10, 1]}, "fields": {"E_magnitude": {"array": "field_E_magnitude_V_per_m", "shape": list(e_array.shape)}, "potential": {"array": "field_potential_V", "shape": list(v_array.shape)}}, "labels": {"array": "labels_mean_max_E_V_per_m", "columns": ["mean_E_V_per_m", "max_E_V_per_m"], "shape": list(labels.shape)}}, "project_file": str(project_file), "checks": checks})
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["traceback"] = traceback.format_exc()
    finally:
        if app is not None:
            try:
                result["release_return"] = app.release_desktop(close_projects=True, close_desktop=True)
            except Exception as exc:
                result["release_error"] = f"{type(exc).__name__}: {exc}"
        result["cleanup"] = cleanup_new_aedt_processes(baseline)
        result["processes_after_close"] = aedt_processes()
        write_json(out / "metadata.json", result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
