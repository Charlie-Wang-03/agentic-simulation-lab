"""Case A: bilinear isotropic hardening uniaxial load/unload."""

from __future__ import annotations

from solid_materials_common import *

CASE = "plasticity"
E, NU, SY, ET = 200e9, 0.30, 250e6, 2e9
L, W, H = 0.10, 0.01, 0.01
STRESSES = [0, 50e6, 100e6, 150e6, 200e6, 250e6, 275e6, 300e6, 225e6, 150e6, 75e6, 0]


def main() -> int:
    p = clean_case(CASE); raw = p["dir"] / "plasticity_raw.csv"
    load_commands = []
    for i, stress in enumerate(STRESSES[1:], 1):
        load_commands.append(f"""TIME,{i}\nNSEL,S,LOC,X,{L}\nFDELE,ALL,FX\nF,ALL,FX,{stress*W*H/4}\nALLSEL\nSOLVE""")
    apdl = f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,SOLID185
MP,EX,1,{E}
MP,PRXY,1,{NU}
TB,PLASTIC,1,,,BISO
TBDATA,1,{SY},{ET}
BLOCK,0,{L},0,{W},0,{H}
ESIZE,{W}
MSHKEY,1
VMESH,ALL
NSEL,S,LOC,X,0
D,ALL,UX,0
NSEL,S,LOC,X,0
NSEL,R,LOC,Y,0
D,ALL,UY,0
NSEL,S,LOC,X,0
NSEL,R,LOC,Z,0
D,ALL,UZ,0
ALLSEL
FINISH
/SOLU
ANTYPE,STATIC
NLGEOM,OFF
KBC,0
NSUBST,10,100,1
OUTRES,ALL,ALL
{chr(10).join(load_commands)}
FINISH
/POST1
*CFOPEN,'{ap(raw)}','csv'
*DO,II,1,{len(STRESSES)-1}
SET,II,LAST
*GET,TT,ACTIVE,0,SET,TIME
NSEL,S,LOC,X,{L}
*GET,NN,NODE,0,COUNT
*GET,NID,NODE,0,NUM,MIN
USUM=0
*DO,JJ,1,NN
*GET,UU,NODE,NID,U,X
USUM=USUM+UU
NID=NDNEXT(NID)
*ENDDO
UAVG=USUM/NN
ALLSEL
NSEL,S,LOC,X,0
FSUM
*GET,RF,FSUM,0,ITEM,FX
ALLSEL
ETABLE,EPPLX,EPPL,X
ETABLE,EPEQ,EPPL,EQV
SSUM
*GET,PSUM,SSUM,0,ITEM,EPPLX
*GET,EQSUM,SSUM,0,ITEM,EPEQ
*GET,NE,ELEM,0,COUNT
PAVG=PSUM/NE
EQAVG=EQSUM/NE
SAVG=RF/({W*H})
*VWRITE,TT,UAVG,SAVG,PAVG,EQAVG
(E22.14,',',E22.14,',',E22.14,',',E22.14,',',E22.14)
*ENDDO
*CFCLOS
/EXIT,NOSAVE
"""
    run_apdl(CASE, apdl)
    got = numeric_rows(raw, ["step", "ux_m", "stress_pa", "plastic_strain", "equivalent_plastic_strain"])
    rows = [{"step": 0, "stress_pa": 0.0, "total_strain": 0.0, "elastic_strain": 0.0, "plastic_strain": 0.0, "equivalent_plastic_strain":0.0, "theory_total_strain": 0.0}]
    for r in got:
        target = STRESSES[round(r["step"])]
        theory = target/E if target <= SY and r["step"] <= 6 else None
        if r["step"] <= 7:
            theory = target/E if target <= SY else SY/E + (target-SY)/ET
        else:
            emax = SY/E + (STRESSES[7]-SY)/ET
            theory = emax - (STRESSES[7]-target)/E
        rows.append({"step": r["step"], "stress_pa": r["stress_pa"], "total_strain": r["ux_m"]/L,
                     "elastic_strain": r["stress_pa"]/E, "plastic_strain": r["plastic_strain"], "equivalent_plastic_strain":r["equivalent_plastic_strain"], "theory_total_strain": theory})
    residual = rows[-1]["total_strain"]; theory_res = SY/E+(300e6-SY)/ET-300e6/E
    max_err = max(rel_error(r["total_strain"], r["theory_total_strain"]) for r in rows[1:] if abs(r["theory_total_strain"]) > 1e-10)
    checks = {"yield_reached": max(r["plastic_strain"] for r in rows) > 1e-5, "residual_strain_positive": residual > 0,
              "reaction_stress_matches_load": max(abs(rows[i]["stress_pa"]-STRESSES[i])/max(STRESSES[i],1) for i in range(1,len(rows)))<.01,
              "residual_error_below_5pct": rel_error(residual, theory_res) < .05, "curve_error_below_8pct": max_err < .08}
    data = payload("A", "Bilinear plasticity load/unload", "TB,PLASTIC,,,,BISO", "Nonlinear static", {"element":"SOLID185","nominal_elements":10},
        {"E_pa":E,"nu":NU,"yield_stress_pa":SY,"tangent_modulus_pa":ET,"stress_history_pa":STRESSES},
        {"residual_strain":residual,"maximum_axial_plastic_strain":max(r["plastic_strain"] for r in rows),"maximum_equivalent_plastic_strain":max(r["equivalent_plastic_strain"] for r in rows)},
        {"residual_strain":theory_res,"formula":"bilinear loading followed by elastic unloading"}, {"maximum_curve_relative_error":max_err,"residual_relative_error":rel_error(residual,theory_res)}, checks, [p["input"],p["solver"],p["log"],raw])
    return finish(CASE,data,rows,[([r["total_strain"] for r in rows],[r["stress_pa"]/1e6 for r in rows],"MAPDL"),([r["theory_total_strain"] for r in rows],[r["stress_pa"]/1e6 for r in rows],"bilinear theory")],("Strain","Stress [MPa]"))


if __name__ == "__main__": raise SystemExit(main())
