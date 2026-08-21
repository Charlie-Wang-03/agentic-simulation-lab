"""MAPDL nonlinear-transient smoke test for an elastic block impact."""

from __future__ import annotations

import math
from datetime import datetime, timezone

from dynamics_smoke_common import OUT, apdl_path, read_numeric_csv, run_mapdl, svg_plot, write_csv, write_json


WIDTH = 0.020
HEIGHT = 0.020
THICKNESS = 0.020
GAP = 0.002
DENSITY = 1000.0
YOUNGS_MODULUS = 1.0e7
POISSON_RATIO = 0.30
INITIAL_VELOCITY = -1.0
END_TIME = 0.008
TIME_STEP = 2.0e-5

INPUT = OUT / "impact.inp"
SOLVER_OUT = OUT / "impact_solver.out"
RAW = OUT / "impact_raw.csv"
HISTORY = OUT / "impact_history.csv"
RESULT = OUT / "impact_results.json"
PLOT = OUT / "impact_response.svg"


def apdl() -> str:
    return f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,PLANE182
KEYOPT,1,3,3
R,1,{THICKNESS}
MP,EX,1,{YOUNGS_MODULUS}
MP,PRXY,1,{POISSON_RATIO}
MP,DENS,1,{DENSITY}
BLC4,0,{GAP},{WIDTH},{HEIGHT}
TYPE,1
REAL,1
MAT,1
ESIZE,0.005
AMESH,ALL
NSEL,S,LOC,X,{WIDTH/2}
NSEL,R,LOC,Y,{GAP + HEIGHT/2}
*GET,TRACK,NODE,0,NUM,MIN
ALLSEL,ALL
ET,2,TARGE169
ET,3,CONTA172
KEYOPT,3,2,0
KEYOPT,3,10,2
R,2
N,1001,-0.05,0,0
N,1002,0.07,0,0
TYPE,2
REAL,2
E,1002,1001
D,1001,ALL,0
D,1002,ALL,0
NSEL,S,LOC,Y,{GAP}
NSEL,R,LOC,X,0,{WIDTH}
TYPE,3
REAL,2
MAT,1
ESURF
ALLSEL,ALL
ESEL,S,TYPE,,1
NSLE,S
IC,ALL,UY,0,{INITIAL_VELOCITY}
ALLSEL,ALL
FINISH
/SOLU
ANTYPE,TRANS
TRNOPT,FULL
NLGEOM,ON
NROPT,FULL
KBC,1
AUTOTS,ON
DELTIM,{TIME_STEP},{TIME_STEP/4},{TIME_STEP}
OUTRES,ALL,ALL
TIME,{END_TIME}
SOLVE
FINISH
/POST1
*GET,NSETS,ACTIVE,0,SET,NSET
*DIM,CSTATV,ARRAY,1000
*DIM,CPRESV,ARRAY,1000
*CFOPEN,'{apdl_path(RAW.with_suffix(''))}','csv'
*DO,II,1,NSETS
SET,1,II
*GET,TT,ACTIVE,0,SET,TIME
*GET,UY,NODE,TRACK,U,Y
ALLSEL,ALL
ESEL,S,TYPE,,1
NSLE,S
*GET,NN,NODE,0,COUNT
NID=0
VYSUM=0
AYSUM=0
*DO,JJ,1,NN
NID=NDNEXT(NID)
*GET,VYN,NODE,NID,V,Y
*GET,AYN,NODE,NID,A,Y
VYSUM=VYSUM+VYN
AYSUM=AYSUM+AYN
*ENDDO
VY=VYSUM/NN
AY=AYSUM/NN
ESEL,S,TYPE,,3
ETABLE,CSTAT,CONT,STAT
ETABLE,CPRES,CONT,PRES
*VGET,CSTATV(1),ELEM,1,ETAB,CSTAT
*VGET,CPRESV(1),ELEM,1,ETAB,CPRES
*VSCFUN,STATMAX,MAX,CSTATV(1)
*VSCFUN,PMAX,MAX,CPRESV(1)
*VWRITE,TT,UY,VY,AY,STATMAX,PMAX
(E20.12,',',E20.12,',',E20.12,',',E20.12,',',E20.12,',',E20.12)
ALLSEL,ALL
*ENDDO
*CFCLOS
FINISH
/EXIT,NOSAVE
"""


def main() -> int:
    OUT.mkdir(exist_ok=True)
    for path in (INPUT, SOLVER_OUT, RAW, HISTORY, RESULT, PLOT):
        path.unlink(missing_ok=True)
    INPUT.write_text(apdl(), encoding="ascii")
    if run_mapdl("impact", INPUT, SOLVER_OUT, timeout=300):
        return 1

    columns = ["time_s", "displacement_y_m", "velocity_y_m_s", "acceleration_y_m_s2", "contact_status", "max_contact_pressure_pa"]
    rows = read_numeric_csv(RAW, columns)
    if len(rows) < 100:
        raise RuntimeError(f"Expected impact history, got {len(rows)} samples")

    block_mass = DENSITY * WIDTH * HEIGHT * THICKNESS
    for row in rows:
        row["impact_force_from_inertial_balance_n"] = block_mass * abs(row["acceleration_y_m_s2"])
        row["contact_force_pressure_area_upper_estimate_n"] = row["max_contact_pressure_pa"] * WIDTH * THICKNESS

    contact_rows = [row for row in rows if row["max_contact_pressure_pa"] > 1.0]
    if not contact_rows:
        raise RuntimeError("No closed/near contact state was found")
    first_contact_time = contact_rows[0]["time_s"]
    post_contact_rows = [row for row in rows if row["time_s"] >= first_contact_time]
    rebound_velocity = max(row["velocity_y_m_s"] for row in post_contact_rows)
    incident_ke = 0.5 * block_mass * INITIAL_VELOCITY**2
    rebound_ke = 0.5 * block_mass * max(0.0, rebound_velocity) ** 2
    restitution_from_velocity = max(0.0, rebound_velocity) / abs(INITIAL_VELOCITY)
    energy_ratio = rebound_ke / incident_ke

    write_csv(HISTORY, rows)
    times = [row["time_s"] for row in rows]
    svg_plot(
        PLOT,
        [
            (times, [row["velocity_y_m_s"] for row in rows], "vertical velocity"),
            (times, [row["displacement_y_m"] * 100.0 for row in rows], "displacement x100"),
        ],
        "Elastic block impact on a fixed plane",
        "Time (s)",
        "Velocity (m/s), displacement x100 (m)",
    )

    peak_pressure = max(row["max_contact_pressure_pa"] for row in rows)
    peak_inertial_force = max(row["impact_force_from_inertial_balance_n"] for row in rows)
    peak_pressure_area_force = max(row["contact_force_pressure_area_upper_estimate_n"] for row in rows)
    checks = {
        "history_available": len(rows) >= 100,
        "contact_occurred": max(row["contact_status"] for row in rows) >= 1,
        "contact_pressure_positive": peak_pressure > 1.0e3,
        "velocity_reversed": rebound_velocity > 0.10,
        "impact_force_positive": peak_inertial_force > 0.1 and peak_pressure_area_force > 0.1,
        "energy_order_of_magnitude": 0.05 < energy_ratio < 1.25,
        "finite_results": all(math.isfinite(value) for row in rows for value in row.values()),
    }
    payload = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "analysis": "MAPDL implicit full transient with deformable PLANE182 block and frictionless TARGE169/CONTA172 impact contact",
        "model": {
            "block_width_m": WIDTH,
            "block_height_m": HEIGHT,
            "thickness_m": THICKNESS,
            "initial_gap_m": GAP,
            "density_kg_m3": DENSITY,
            "block_mass_kg": block_mass,
            "youngs_modulus_pa": YOUNGS_MODULUS,
            "poisson_ratio": POISSON_RATIO,
            "initial_velocity_y_m_s": INITIAL_VELOCITY,
            "end_time_s": END_TIME,
            "nominal_time_step_s": TIME_STEP,
        },
        "results": {
            "sample_count": len(rows),
            "first_contact_time_s": first_contact_time,
            "minimum_displacement_y_m": min(row["displacement_y_m"] for row in rows),
            "minimum_velocity_y_m_s": min(row["velocity_y_m_s"] for row in rows),
            "maximum_rebound_velocity_y_m_s": rebound_velocity,
            "velocity_restitution_estimate": restitution_from_velocity,
            "incident_kinetic_energy_j": incident_ke,
            "rebound_kinetic_energy_j": rebound_ke,
            "rebound_to_incident_energy_ratio": energy_ratio,
            "maximum_contact_status": max(row["contact_status"] for row in rows),
            "maximum_contact_pressure_pa": peak_pressure,
            "peak_impact_force_from_inertial_balance_n": peak_inertial_force,
            "peak_contact_force_pressure_area_upper_estimate_n": peak_pressure_area_force,
        },
        "force_note": "The transient solver supplies acceleration and peak pressure. The reported impact-force values are, respectively, mass times the absolute block-node-average acceleration and peak-pressure times nominal face area; the latter is an upper estimate, not an integrated contact resultant.",
        "checks": checks,
        "files": {"history_csv": str(HISTORY), "plot_svg": str(PLOT), "solver_output": str(SOLVER_OUT)},
    }
    write_json(RESULT, payload)
    print(payload, flush=True)
    print("CASE D", payload["status"], flush=True)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
