"""Case C: cavity-plus-neck Helmholtz resonator harmonic sweep."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from acoustics_common import AIR_DENSITY, SOUND_SPEED, apdl_stem, complex_metrics, dominant_peak, ensure_dirs, read_numeric_rows, run_apdl, svg_plot, write_json


CASE = "case_c_helmholtz"
CAVITY = 0.30
NECK_LENGTH = 0.12
NECK_WIDTH = 0.05
NECK_Y0 = (CAVITY - NECK_WIDTH) / 2
NECK_Z0 = NECK_Y0
MESH_SIZE = 0.025
FREQUENCIES = np.arange(25.0, 71.0, 1.0)


def preamble() -> str:
    return f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,FLUID221,,1
MP,DENS,1,{AIR_DENSITY:.12g}
MP,SONC,1,{SOUND_SPEED:.12g}
MP,DMPR,1,0.005
BLOCK,0,{CAVITY},0,{CAVITY},0,{CAVITY}
BLOCK,{CAVITY},{CAVITY+NECK_LENGTH},{NECK_Y0},{NECK_Y0+NECK_WIDTH},{NECK_Z0},{NECK_Z0+NECK_WIDTH}
VGLUE,ALL
MSHKEY,0
ESIZE,{MESH_SIZE}
TYPE,1
MAT,1
VMESH,ALL
ALLSEL,ALL
NSEL,S,LOC,X,{CAVITY+NECK_LENGTH}
D,ALL,PRES,1,0
ALLSEL,ALL
NSEL,S,LOC,X,0.14,0.16
NSEL,R,LOC,Y,0.14,0.16
NSEL,R,LOC,Z,0.14,0.16
*GET,PCAV,NODE,0,NUM,MIN
ALLSEL,ALL
NSEL,S,LOC,X,{CAVITY+0.02},{CAVITY+0.05}
NSEL,R,LOC,Y,{NECK_Y0},{NECK_Y0+NECK_WIDTH}
NSEL,R,LOC,Z,{NECK_Z0},{NECK_Z0+NECK_WIDTH}
*GET,PNEAR,NODE,0,NUM,MIN
ALLSEL,ALL
NSEL,S,LOC,X,{CAVITY+0.075},{CAVITY+0.10}
NSEL,R,LOC,Y,{NECK_Y0},{NECK_Y0+NECK_WIDTH}
NSEL,R,LOC,Z,{NECK_Z0},{NECK_Z0+NECK_WIDTH}
*GET,PFAR,NODE,0,NUM,MIN
ALLSEL,ALL
"""


def build_apdl(csv_path: Path) -> str:
    lines = [preamble(), f"*CFOPEN,'{apdl_stem(csv_path)}','csv'", "*VWRITE,0,0,0,0,0,0,0", "(F12.4,6(',',E22.14))", "*CFCLOS"]
    for freq in FREQUENCIES:
        lines += ["/SOLU", "ANTYPE,HARM", "HROPT,FULL", f"HARFRQ,{freq}", "NSUBST,1", "KBC,1", "SOLVE", "FINISH", "/POST1", "SET,LAST,,,0", "*GET,CR,NODE,PCAV,PRES", "*GET,NR,NODE,PNEAR,PRES", "*GET,FR,NODE,PFAR,PRES", "SET,LAST,,,1", "*GET,CI,NODE,PCAV,PRES", "*GET,NI,NODE,PNEAR,PRES", "*GET,FI,NODE,PFAR,PRES", f"*CFOPEN,'{apdl_stem(csv_path)}','csv',,APPEND", f"*VWRITE,{freq},CR,CI,NR,NI,FR,FI", "(F12.4,6(',',E22.14))", "*CFCLOS", "FINISH"]
    return "\n".join(lines + ["/EXIT,NOSAVE"]) + "\n"


def main() -> int:
    out, _ = ensure_dirs(CASE)
    csv_path = out / "helmholtz_frequency_response.csv"
    csv_path.unlink(missing_ok=True)
    evidence = run_apdl(CASE, build_apdl(csv_path), timeout=360)
    rows = [r for r in read_numeric_rows(csv_path, ["frequency_hz", "cavity_real", "cavity_imag", "neck1_real", "neck1_imag", "neck2_real", "neck2_imag"]) if r["frequency_hz"] > 0]
    for r in rows:
        r["cavity_amplitude_pa"], r["cavity_phase_deg"] = complex_metrics(r["cavity_real"], r["cavity_imag"])
        dp = complex(r["neck2_real"]-r["neck1_real"], r["neck2_imag"]-r["neck1_imag"])
        omega = 2*math.pi*r["frequency_hz"]
        velocity = 1j*dp/(omega*AIR_DENSITY*0.06)
        r["neck_velocity_m_s"] = abs(velocity)
    peak_f, peak_p, _ = dominant_peak([r["frequency_hz"] for r in rows], [r["cavity_amplitude_pa"] for r in rows])
    area = NECK_WIDTH**2
    volume = CAVITY**3
    req = math.sqrt(area/math.pi)
    effective_length = NECK_LENGTH + 1.7*req
    theory = SOUND_SPEED/(2*math.pi)*math.sqrt(area/(volume*effective_length))
    error = abs(peak_f-theory)/theory
    plot = out / "helmholtz_response.svg"
    svg_plot(plot, [([r["frequency_hz"] for r in rows], [r["cavity_amplitude_pa"] for r in rows], "cavity pressure")], "Helmholtz resonator response", "Frequency (Hz)", "Pressure amplitude (Pa)")
    checks = {"frequency_sweep_complete": len(rows)==len(FREQUENCIES), "resonance_error_below_15pct": error<0.15, "neck_velocity_nonzero": max(r["neck_velocity_m_s"] for r in rows)>0, "resonance_peak_present": peak_p>2.0}
    payload = {"case":"C","title":"Helmholtz resonator","status":"PASS" if all(checks.values()) else "FAIL","solver":"Ansys MAPDL 261","element":"FLUID221 KEYOPT(2)=1","analysis_type":"full harmonic acoustic sweep","geometry":{"cavity_volume_m3":volume,"neck_area_m2":area,"neck_physical_length_m":NECK_LENGTH,"neck_effective_length_m":effective_length,"end_correction":"1.7*r_eq"},"acoustic_material":{"density_kg_m3":AIR_DENSITY,"sound_speed_m_s":SOUND_SPEED},"mesh":{"nominal_size_m":MESH_SIZE,"topology":"quadratic tetrahedra"},"results":{"resonance_frequency_hz":peak_f,"peak_cavity_pressure_pa":peak_p,"maximum_neck_velocity_m_s":max(r["neck_velocity_m_s"] for r in rows)},"theory":{"formula":"c/(2*pi)*sqrt(A/(V*L_eff))","frequency_hz":theory},"errors":{"relative_frequency_error":error},"checks":checks,"files":[str(csv_path.resolve()),str(plot.resolve()),evidence["solver_output"]]}
    write_json(out/"case_c_results.json",payload)
    print(payload)
    return 0 if payload["status"]=="PASS" else 1


if __name__=="__main__": raise SystemExit(main())
