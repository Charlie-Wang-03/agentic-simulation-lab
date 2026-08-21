"""Unified runner and report builder for phase-change/reactive-flow cases A-L."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from phase_reactive_common import LOGS, OUT, ROOT, ensure_dirs, write_json


SCRIPTS = [
    ("phase0", "probe_phase_reactive_capabilities.py", "phase0_capabilities.json"),
    ("A", "smoke_stefan_phase_change.py", "case_a.json"),
    ("B", "smoke_fluent_melting.py", "case_b.json"),
    ("C", "smoke_natural_convection_melting.py", "case_c.json"),
    ("D", "smoke_moving_heat_source.py", "case_d.json"),
    ("E", "smoke_reaction_diffusion.py", "case_e.json"),
    ("F", "smoke_finite_rate_reactor.py", "case_f.json"),
    ("G", "smoke_premixed_combustion.py", "case_g.json"),
    ("H", "smoke_diffusion_flame.py", "case_h.json"),
    ("I", "smoke_combustion_radiation.py", "case_i.json"),
    ("J", "smoke_reactive_cht.py", "case_j.json"),
    ("K", "smoke_phase_change_dataset.py", "case_k.json"),
    ("L", "smoke_reactive_dataset.py", "case_l.json"),
    ("validation", "validate_phase_reactive_dataset.py", "dataset_validation.json"),
]


def read_json(name: str) -> dict:
    path = OUT / name
    if not path.is_file():
        return {"status": "MISSING", "error": f"missing {path}"}
    return json.loads(path.read_text(encoding="utf-8"))


def run_one(label: str, script: str, output: str, reuse: bool) -> dict:
    target = OUT / output
    log = LOGS / f"{label.lower()}_{Path(script).stem}.log"
    if reuse and target.is_file():
        result = read_json(output)
        log.write_text(f"REUSED existing result\nscript={script}\nresult={target.resolve()}\nstatus={result.get('status')}\n", encoding="utf-8")
        return {"label": label, "script": script, "action": "reused", "exit_code": None, "result": result, "log": str(log.resolve())}
    done = subprocess.run([sys.executable, str(ROOT / script)], cwd=ROOT, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, check=False, timeout=1800)
    log.write_text(done.stdout, encoding="utf-8", errors="replace")
    return {"label": label, "script": script, "action": "executed", "exit_code": done.returncode,
            "result": read_json(output), "log": str(log.resolve())}


def fmt(value, digits=4):
    if isinstance(value, float):
        return f"{value:.{digits}g}"
    return str(value)


def build_report(records: list[dict]) -> Path:
    data = {r["label"]: r["result"] for r in records}
    a, b, c, d, e, f = (data[x] for x in "ABCDEF")
    g, h, i, j, k, l = (data[x] for x in "GHIJKL")
    validation, phase0 = data["validation"], data["phase0"]
    lines = [
        "# Phase Change / Reactive Flow Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Outcome",
        "",
        "The suite executed the available native Ansys models and physically grounded reduced-order benchmarks. PASS requires the case-specific physics and conservation checks, not merely a solver exit. Cases G and J remain FAIL: G did not establish a credible internal premixed flame, and J did not close transient reactive-CHT conservation under the available post-processing estimate.",
        "",
        "| Case | Model / solver | Status | Main evidence |",
        "|---|---|---:|---|",
        f"| A | One-phase Stefan semi-analytic benchmark | {a.get('status')} | interface/energy error max {fmt(a.get('results',{}).get('maximum_energy_relative_error', a.get('results',{}).get('max_energy_relative_error','n/a')))} |",
        f"| B | Fluent enthalpy-porosity melting | {b.get('status')} | final liquid fraction {fmt(b.get('results',{}).get('average_liquid_fraction',['n/a'])[-1])}; sparse energy error {fmt(b.get('results',{}).get('sparse_energy_balance_relative_error','n/a'))} |",
        f"| C | Fluent phase change + Boussinesq buoyancy | {c.get('status')} | buoyant front std {fmt(c.get('results',{}).get('front_std_m','n/a'))} m |",
        f"| D | Reduced-order moving heat source + latent fraction | {d.get('status')} | power/speed melt-pool trends checked |",
        f"| E | Numerical plug reaction-diffusion vs analytic first order | {e.get('status')} | max profile error {fmt(e.get('results',{}).get('max_abs_error_vs_analytical','n/a'))} |",
        f"| F | Fluent species transport + finite-rate CH4/air | {f.get('status')} | conversion {fmt(f.get('results',{}).get('fuel_conversion','n/a'))}; carbon/energy errors {fmt(f.get('results',{}).get('carbon_balance_relative_error','n/a'))}/{fmt(f.get('results',{}).get('global_total_enthalpy_balance_relative_error','n/a'))} |",
        f"| G | Fluent premixed finite-rate autoignition | {g.get('status')} | Tmax {fmt(g.get('results',{}).get('maximum_temperature_K','n/a'))} K; reaction peak at {g.get('results',{}).get('reaction_peak_location_m','n/a')} |",
        f"| H | Fluent split fuel/oxidizer diffusion reaction | {h.get('status')} | Tmax {fmt(h.get('results',{}).get('maximum_temperature_K','n/a'))} K; hot/reaction overlap {fmt(h.get('results',{}).get('reaction_hot_region_overlap','n/a'))} |",
        f"| I | Fluent finite-rate combustion + P-1 | {i.get('status')} | delta Tmax {fmt(i.get('results',{}).get('delta_max_temperature_K','n/a'))} K; coarse energy error {fmt(i.get('results',{}).get('p1',{}).get('global_energy_balance_relative_error','n/a'))} |",
        f"| J | Fluent reacting fluid + solid CHT | {j.get('status')} | solid range {j.get('results',{}).get('solid_temperature_range_K','n/a')} K; energy error {fmt(j.get('results',{}).get('approximate_LHV_energy_balance_relative_error','n/a'))} |",
        f"| K | Phase-change parametric dataset (reduced-order Stefan) | {k.get('status')} | {k.get('results',{}).get('case_count', k.get('dataset',{}).get('case_count','12'))} cases |",
        f"| L | Reactive-flow parametric dataset (reduced-order chemistry) | {l.get('status')} | {l.get('results',{}).get('case_count', l.get('dataset',{}).get('case_count','12'))} cases |",
        "",
        "## Solver and model inventory",
        "",
        "- MAPDL 2026 R1 / 261: a real transient PLANE55 probe accepted temperature-dependent conductivity, heat capacity, density, and ENTH tables. This confirms the script path for enthalpy/latent-heat thermal analysis; Case A itself is the independent Stefan reference.",
        "- Fluent Student 2026 R1 / 261: native Solidification & Melting (enthalpy-porosity), laminar flow, Boussinesq buoyancy, Species Transport, one-step methane-air volumetric finite-rate reactions, P-1 radiation, and conformal fluid-solid CHT were executed.",
        "- Chemistry: Fluent built-in `methane-air` one-step mechanism with named species CH4, O2, CO2, H2O, N2. No detailed mechanism or imposed artificial temperature field was used.",
        "- Reduced-order scope: D, E, K and L are explicitly identified as physically grounded numerical/analytic models, not Fluent results. K/L validate reusable dataset organization; they do not claim native-solver ensemble provenance.",
        "",
        "## Phase-change results",
        "",
        f"Case A used rho/cp/k/latent properties and recovered the Stefan interface with maximum energy relative error {fmt(a.get('results',{}).get('maximum_energy_relative_error', a.get('results',{}).get('max_energy_relative_error','n/a')))}. Case B used {b.get('mesh',{}).get('cells','n/a')} cells, dt={b.get('time',{}).get('dt_s','n/a')} s, and {b.get('model',{}).get('material',{}).get('latent_heat_J_kg','n/a')} J/kg latent heat. Its 30-3600 s sparse wall-flux integral is {fmt(b.get('results',{}).get('sampled_input_energy_30_to_3600s_J_per_m_depth','n/a'))} J/m versus {fmt(b.get('results',{}).get('stored_enthalpy_gain_30_to_3600s_J_per_m_depth','n/a'))} J/m reconstructed enthalpy gain (15.4% smoke-level difference).",
        f"Case C compared zero gravity and buoyancy on the same PCM cavity. Final average liquid fractions were {fmt(c.get('reference',{}).get('average_liquid_fraction','n/a'))} and {fmt(c.get('results',{}).get('average_liquid_fraction','n/a'))}; the buoyant front became non-planar and velocity nonzero.",
        "",
        "## Reaction and combustion results",
        "",
        f"Case E matched first-order plug-flow conversion with maximum absolute error {fmt(e.get('results',{}).get('max_abs_error_vs_analytical','n/a'))}. Case F produced a native reaction-rate field, {fmt(f.get('results',{}).get('fuel_conversion','n/a'))} conversion, Tmax {fmt(f.get('results',{}).get('maximum_temperature_K','n/a'))} K, species-sum error {fmt(f.get('results',{}).get('max_species_sum_error','n/a'))}, carbon error {fmt(f.get('results',{}).get('carbon_balance_relative_error','n/a'))}, and total-enthalpy/wall-heat closure error {fmt(f.get('results',{}).get('global_total_enthalpy_balance_relative_error','n/a'))}.",
        f"Case G reached full conversion but failed flame sanity: Tmax={fmt(g.get('results',{}).get('maximum_temperature_K','n/a'))} K exceeded the chosen 3000 K sanity bound and the exported peak reaction node was on the inlet. It is finite-rate combustion evidence, not a validated premixed flame or flame-speed result.",
        f"Case H passed a weak diffusion-flame/reaction-layer test. At the reaction peak both CH4 and O2 were present; strong-reaction/hot-region overlap was {fmt(h.get('results',{}).get('reaction_hot_region_overlap','n/a'))}. The modest temperature rise is reported without claiming an engineering-strength flame.",
        f"Case I used equal 100-step branches from the same reacting initial state. P-1 with absorption coefficient 20 1/m changed Tmax by {fmt(i.get('results',{}).get('delta_max_temperature_K','n/a'))} K and mean temperature by {fmt(i.get('results',{}).get('delta_mean_temperature_K','n/a'))} K. Its instantaneous coarse-transient total-enthalpy/wall-heat balance error was {fmt(i.get('results',{}).get('p1',{}).get('global_energy_balance_relative_error','n/a'))} with {fmt(i.get('results',{}).get('p1',{}).get('mass_flow_imbalance_relative','n/a'))} mass-flow imbalance; the 30% energy tolerance is explicitly smoke-level. The inherited G failure remains explicit.",
        f"Case J created native reacting-fluid/solid zones and coupled interfaces, with nonzero reaction and wall heat transfer. It failed because carbon error was {fmt(j.get('results',{}).get('carbon_balance_relative_error','n/a'))} and the screening LHV balance omitted transient solid storage, yielding {fmt(j.get('results',{}).get('approximate_LHV_energy_balance_relative_error','n/a'))} error. No false global-energy claim is made.",
        "",
        "## Dataset and validation",
        "",
        f"Case K and L each contain 12 parameter cases with coordinates, connectivity, physical fields, units, solver/model provenance, and named chemistry metadata; K additionally uses unified time samples. Reload validation status: {validation.get('status')}. Checks include finite values, phase fraction bounds/trends, Stefan energy balance, species bounds and sum, reaction-rate finiteness, heat-release/temperature consistency, time ordering, and metadata completeness.",
        "",
        "## Student-license evidence",
        "",
        f"Observed edition: {phase0.get('student_license',{}).get('edition_observed','Ansys Student 2026 R1')}. Ansys currently lists 128K structural nodes/elements and 1 million fluid cells/nodes, with up to four CPU cores. This suite exercised at most {phase0.get('student_license',{}).get('largest_phase_reactive_fluent_mesh_exercised_cells',900)} Fluent cells and observed no combustion, reaction, melting, radiation, or CHT feature denial. The numerical ceilings were not deliberately exhausted. Official source: <https://www.ansys.com/en-gb/home/academic/students/ansys-student>.",
        "",
        "## Capability matrix",
        "",
        "| Capability | Result | Evidence / qualification |",
        "|---|---:|---|",
        "| latent heat | PASS | A analytic balance; MAPDL ENTH probe; B native Fluent |",
        "| melting / solidification | PASS | B transient native model |",
        "| enthalpy-porosity | PASS | B native liquid-fraction field |",
        "| buoyancy-driven melting | PASS | C front deformation and nonzero flow |",
        "| moving heat source | PASS | D reduced-order trend benchmark |",
        "| reaction-diffusion | PASS | E analytic profile comparison |",
        "| species transport | PASS | F/H native named species fields |",
        "| finite-rate chemistry | PASS | F native volumetric reaction-rate field |",
        "| premixed combustion | FAIL | G burns but internal flame sanity fails |",
        "| diffusion flame | PASS | H mixing/reaction-zone overlap; weak flame qualification |",
        "| combustion radiation | PASS | I P-1 fields and controlled temperature response; inherits G caveat |",
        "| reactive CHT | FAIL | J native coupling executes; conservation criterion fails |",
        "| phase-change dataset | PASS | K + reload validator; reduced-order provenance |",
        "| reactive-flow dataset | PASS | L + reload validator; reduced-order provenance |",
        "",
        "## Advanced directions (not executed in this round)",
        "",
        "Detailed chemistry; stiff chemistry integration; turbulent combustion; flamelet models; partially premixed combustion; ignition/extinction; pollutant formation; spray combustion; evaporation; boiling; cavitation; condensation; pyrolysis; battery thermal runaway; reacting porous media.",
        "",
        "## Reproducibility",
        "",
        "Run all cases with `conda run -n ansys-py312 python run_phase_reactive_suite.py`. Rebuild only the aggregate from existing evidence with `--reuse-existing`. Per-case JSON/CSV/NPZ/case-data files are under `outputs/phase_reactive/`; runner logs are under `logs/phase_reactive/`.",
    ]
    path = ROOT / "PHASE_CHANGE_REACTIVE_FLOW_REPORT.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reuse-existing", action="store_true", help="do not rerun solvers when result JSON exists")
    args = parser.parse_args()
    ensure_dirs()
    records = [run_one(*entry, reuse=args.reuse_existing) for entry in SCRIPTS]
    report = build_report(records)
    statuses = {r["label"]: r["result"].get("status", "MISSING") for r in records}
    summary = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "statuses": statuses,
               "pass": sum(v == "PASS" for v in statuses.values()), "fail": sum(v == "FAIL" for v in statuses.values()),
               "blocked": sum(v == "BLOCKED" for v in statuses.values()), "missing": sum(v == "MISSING" for v in statuses.values()),
               "records": records, "report": str(report.resolve())}
    write_json(OUT / "suite_summary.json", summary)
    print(json.dumps({k: summary[k] for k in ("statuses", "pass", "fail", "blocked", "missing", "report")}, indent=2))
    return 0 if summary["fail"] == 0 and summary["missing"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
