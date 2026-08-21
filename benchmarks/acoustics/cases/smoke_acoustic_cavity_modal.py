"""Case B: closed rectangular acoustic cavity modal benchmark."""

from __future__ import annotations

import itertools
import math
from pathlib import Path

from acoustics_common import AIR_DENSITY, SOUND_SPEED, apdl_stem, ensure_dirs, read_numeric_rows, run_apdl, write_json


CASE = "case_b_cavity_modal"
LX, LY, LZ = 0.60, 0.40, 0.30
MESH_SIZE = 0.05
MODE_COUNT = 8


def theory_modes(count: int) -> list[dict]:
    modes = []
    for n, m, p in itertools.product(range(5), repeat=3):
        if n == m == p == 0:
            continue
        f = SOUND_SPEED / 2.0 * math.sqrt((n/LX)**2 + (m/LY)**2 + (p/LZ)**2)
        modes.append({"indices": [n, m, p], "frequency_hz": f})
    return sorted(modes, key=lambda x: x["frequency_hz"])[:count]


def build_apdl(freq_csv: Path, field_csv: Path) -> str:
    return f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,FLUID30,,1
MP,DENS,1,{AIR_DENSITY:.12g}
MP,SONC,1,{SOUND_SPEED:.12g}
BLOCK,0,{LX},0,{LY},0,{LZ}
MSHKEY,1
ESIZE,{MESH_SIZE}
TYPE,1
MAT,1
VMESH,ALL
ALLSEL,ALL
/SOLU
ANTYPE,MODAL
MODOPT,LANB,{MODE_COUNT},1
MXPAND,{MODE_COUNT},,,,YES
SOLVE
FINISH
/POST1
*CFOPEN,'{apdl_stem(freq_csv)}','csv'
*DO,II,1,{MODE_COUNT}
SET,1,II
*GET,FF,ACTIVE,0,SET,FREQ
*VWRITE,II,FF
(F12.0,',',E22.14)
*ENDDO
*CFCLOS
SET,1,1
ALLSEL,ALL
*GET,NC,NODE,0,COUNT
*GET,NID,NODE,0,NUM,MIN
*CFOPEN,'{apdl_stem(field_csv)}','csv'
*DO,JJ,1,NC
*GET,XX,NODE,NID,LOC,X
*GET,YY,NODE,NID,LOC,Y
*GET,ZZ,NODE,NID,LOC,Z
*GET,PP,NODE,NID,PRES
*VWRITE,NID,XX,YY,ZZ,PP
(F12.0,',',E22.14,',',E22.14,',',E22.14,',',E22.14)
NID=NDNEXT(NID)
*ENDDO
*CFCLOS
FINISH
/EXIT,NOSAVE
"""


def main() -> int:
    out, _ = ensure_dirs(CASE)
    freq_csv, field_csv = out / "eigenfrequencies.csv", out / "mode1_pressure.csv"
    for p in (freq_csv, field_csv): p.unlink(missing_ok=True)
    evidence = run_apdl(CASE, build_apdl(freq_csv, field_csv), timeout=240)
    numerical = read_numeric_rows(freq_csv, ["mode", "frequency_hz"])
    field = read_numeric_rows(field_csv, ["node_id", "x_m", "y_m", "z_m", "pressure_pa"])
    theory = theory_modes(MODE_COUNT)
    comparisons = []
    for num, ref in zip(numerical, theory):
        err = abs(num["frequency_hz"] - ref["frequency_hz"]) / ref["frequency_hz"]
        comparisons.append({"mode": int(num["mode"]), "indices": ref["indices"], "numerical_hz": num["frequency_hz"], "theoretical_hz": ref["frequency_hz"], "relative_error": err})
    max_error = max(x["relative_error"] for x in comparisons) if comparisons else math.inf
    checks = {"mode_count": len(numerical) == MODE_COUNT, "mode_field_saved": len(field) > 100, "maximum_frequency_error_below_4pct": max_error < 0.04, "nonzero_mode_shape": any(abs(x["pressure_pa"]) > 0 for x in field)}
    payload = {"case": "B", "title": "Three-dimensional rectangular acoustic cavity modes", "status": "PASS" if all(checks.values()) else "FAIL", "solver": "Ansys MAPDL 261", "element": "FLUID30 KEYOPT(2)=1", "analysis_type": "modal acoustics (Block Lanczos)", "geometry": {"Lx_m": LX, "Ly_m": LY, "Lz_m": LZ, "boundary": "all natural rigid walls"}, "acoustic_material": {"density_kg_m3": AIR_DENSITY, "sound_speed_m_s": SOUND_SPEED}, "mesh": {"nominal_size_m": MESH_SIZE, "field_node_count": len(field)}, "results": {"modes": comparisons, "maximum_relative_error": max_error}, "theory": {"formula": "c/2*sqrt((n/Lx)^2+(m/Ly)^2+(p/Lz)^2)"}, "errors": {"maximum_relative_error": max_error}, "checks": checks, "files": [str(freq_csv.resolve()), str(field_csv.resolve()), evidence["solver_output"]]}
    write_json(out / "case_b_results.json", payload)
    print(payload)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
