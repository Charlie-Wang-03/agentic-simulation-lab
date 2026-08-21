"""Case A: MAPDL FLUID30 pressure-driven open/closed standing-wave tube."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from acoustics_common import (
    AIR_DENSITY, SOUND_SPEED, apdl_stem, complex_metrics, dominant_peak,
    ensure_dirs, read_numeric_rows, run_apdl, spl_db, svg_plot, write_json,
)


CASE = "case_a_tube"
LENGTH = 1.0
WIDTH = 0.10
MESH_SIZE = 0.025
FREQUENCIES = np.arange(55.0, 121.0, 1.0)


def model_preamble() -> str:
    return f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,FLUID30,,1
MP,DENS,1,{AIR_DENSITY:.12g}
MP,SONC,1,{SOUND_SPEED:.12g}
MP,DMPR,1,0.003
BLOCK,0,{LENGTH},0,{WIDTH},0,{WIDTH}
MSHKEY,1
ESIZE,{MESH_SIZE}
TYPE,1
MAT,1
VMESH,ALL
ALLSEL,ALL
NSEL,S,LOC,X,0
D,ALL,PRES,1,0
ALLSEL,ALL
NSEL,S,LOC,X,{LENGTH}
*GET,PROBE,NODE,0,NUM,MIN
ALLSEL,ALL
"""


def sweep_apdl(csv_path: Path) -> str:
    commands = [model_preamble(), f"*CFOPEN,'{apdl_stem(csv_path)}','csv'", "*VWRITE,0,0,0", "(F14.6,',',E22.14,',',E22.14)", "*CFCLOS"]
    for freq in FREQUENCIES:
        commands += [
            "/SOLU", "ANTYPE,HARM", "HROPT,FULL", f"HARFRQ,{freq:.9g}", "NSUBST,1", "KBC,1", "SOLVE", "FINISH",
            "/POST1", "SET,LAST,,,0", "*GET,PR,NODE,PROBE,PRES", "SET,LAST,,,1", "*GET,PI,NODE,PROBE,PRES",
            f"*CFOPEN,'{apdl_stem(csv_path)}','csv',,APPEND", f"*VWRITE,{freq:.9g},PR,PI", "(F14.6,',',E22.14,',',E22.14)", "*CFCLOS", "FINISH",
        ]
    commands += ["/EXIT,NOSAVE"]
    return "\n".join(commands) + "\n"


def field_apdl(csv_path: Path, freq: float) -> str:
    return model_preamble() + f"""/SOLU
ANTYPE,HARM
HROPT,FULL
HARFRQ,{freq:.12g}
NSUBST,1
KBC,1
SOLVE
FINISH
/POST1
SET,LAST,,,0
NSEL,S,LOC,Y,0
NSEL,R,LOC,Z,0
*GET,NC,NODE,0,COUNT
*GET,NID,NODE,0,NUM,MIN
*CFOPEN,'{apdl_stem(csv_path)}','csv'
*DO,II,1,NC
*GET,XX,NODE,NID,LOC,X
*GET,PR,NODE,NID,PRES
SET,LAST,,,1
*GET,PI,NODE,NID,PRES
SET,LAST,,,0
*VWRITE,NID,XX,PR,PI
(F12.0,',',E22.14,',',E22.14,',',E22.14)
NID=NDNEXT(NID)
*ENDDO
*CFCLOS
ALLSEL,ALL
FINISH
/EXIT,NOSAVE
"""


def main() -> int:
    out, _ = ensure_dirs(CASE)
    sweep_csv = out / "frequency_response.csv"
    field_csv = out / "pressure_axis.csv"
    for p in (sweep_csv, field_csv): p.unlink(missing_ok=True)
    ev1 = run_apdl(CASE + "_sweep", sweep_apdl(sweep_csv), timeout=420)
    rows = [r for r in read_numeric_rows(sweep_csv, ["frequency_hz", "real_pa", "imag_pa"]) if r["frequency_hz"] > 0]
    if len(rows) != len(FREQUENCIES):
        raise RuntimeError(f"Expected {len(FREQUENCIES)} sweep points, got {len(rows)}")
    for row in rows:
        row["amplitude_pa"], row["phase_deg"] = complex_metrics(row["real_pa"], row["imag_pa"])
        row["spl_db"] = spl_db(row["amplitude_pa"])
    peak_f, peak_p, _ = dominant_peak([r["frequency_hz"] for r in rows], [r["amplitude_pa"] for r in rows])
    theory = SOUND_SPEED / (4.0 * LENGTH)
    error = abs(peak_f - theory) / theory
    ev2 = run_apdl(CASE + "_field", field_apdl(field_csv, peak_f), timeout=180)
    field = read_numeric_rows(field_csv, ["node_id", "x_m", "real_pa", "imag_pa"])
    if len(field) < 20:
        raise RuntimeError(f"Axis field extraction too small: {len(field)}")
    field.sort(key=lambda r: r["x_m"])
    for row in field:
        row["amplitude_pa"], row["phase_deg"] = complex_metrics(row["real_pa"], row["imag_pa"])
    plot = out / "standing_wave_response.svg"
    svg_plot(plot, [([r["frequency_hz"] for r in rows], [r["amplitude_pa"] for r in rows], "closed-end pressure")], "Open/closed tube frequency response", "Frequency (Hz)", "Pressure amplitude (Pa)")
    checks = {"solver_points_complete": len(rows) == len(FREQUENCIES), "pressure_finite": all(math.isfinite(r["amplitude_pa"]) for r in rows), "standing_wave_frequency_error_below_5pct": error < 0.05, "axis_field_saved": len(field) >= 20}
    payload = {
        "case": "A", "title": "One-dimensional standing-wave tube", "status": "PASS" if all(checks.values()) else "FAIL",
        "solver": "Ansys MAPDL 261", "element": "FLUID30 KEYOPT(2)=1", "analysis_type": "full harmonic acoustic sweep",
        "geometry": {"length_m": LENGTH, "width_m": WIDTH, "boundary": "prescribed pressure (sound-soft/source) at x=0; rigid termination at x=L"},
        "acoustic_material": {"density_kg_m3": AIR_DENSITY, "sound_speed_m_s": SOUND_SPEED}, "mesh": {"nominal_size_m": MESH_SIZE},
        "results": {"resonance_frequency_hz": peak_f, "peak_pressure_pa": peak_p, "peak_spl_db": spl_db(peak_p), "frequency_points": len(rows), "axis_samples": len(field)},
        "theory": {"formula": "f1=c/(4L)", "frequency_hz": theory}, "errors": {"relative_frequency_error": error}, "checks": checks,
        "files": [str(sweep_csv.resolve()), str(field_csv.resolve()), str(plot.resolve()), ev1["solver_output"], ev2["solver_output"]], "limitations": ["The prescribed-pressure inlet is treated as the pressure node/open end; the opposite end is the natural rigid wall."],
    }
    write_json(out / "case_a_results.json", payload)
    print(payload)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
