"""Case G: orthotropic lamina effective modulus at 0/45/90 degrees."""

from __future__ import annotations

from solid_materials_common import *

CASE="orthotropic"; E1=135e9; E2=10e9; E3=10e9; NU12=.30; NU23=.40; NU13=.30; G12=5e9; G23=3.8e9; G13=5e9
SIGMA=50e6; L=.10; W=.01; H=.01; ANGLES=[0,45,90]


def theory(theta:float)->float:
    import math
    c=math.cos(math.radians(theta)); s=math.sin(math.radians(theta)); S11=1/E1; S22=1/E2; S12=-NU12/E1; S66=1/G12
    return 1/(S11*c**4+S22*s**4+(2*S12+S66)*s*s*c*c)


def main()->int:
    p=clean_case(CASE); raw=p["dir"]/"orthotropic_raw.csv"; prep=[]; extract=[]
    for j,a in enumerate(ANGLES):
        y0=j*.02; cs=20+j
        prep.append(f"""LOCAL,{cs},0,0,0,0,{a}\nCSYS,0\nBLOCK,0,{L},{y0},{y0+W},0,{H}\nVSEL,S,VOLU,,{j+1}\nESYS,{cs}\nESIZE,{W}\nMSHKEY,1\nVMESH,ALL\nALLSEL""")
        extract.append(f"""NSEL,S,LOC,X,{L}\nNSEL,R,LOC,Y,{y0},{y0+W}\n*GET,NN,NODE,0,COUNT\n*GET,NID,NODE,0,NUM,MIN\nUS=0\n*DO,JJ,1,NN\n*GET,UU,NODE,NID,U,X\nUS=US+UU\nNID=NDNEXT(NID)\n*ENDDO\nUA=US/NN\n*VWRITE,{a},UA\n(E22.14,',',E22.14)\nALLSEL""")
    transverse_constraints=''.join(f'NSEL,S,LOC,Y,{j*.02}\nD,ALL,UY,0\nALLSEL\n' for j in range(3))
    apdl=f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,SOLID185
MP,EX,1,{E1}
MP,EY,1,{E2}
MP,EZ,1,{E3}
MP,PRXY,1,{NU12}
MP,PRYZ,1,{NU23}
MP,PRXZ,1,{NU13}
MP,GXY,1,{G12}
MP,GYZ,1,{G23}
MP,GXZ,1,{G13}
{chr(10).join(prep)}
NSEL,S,LOC,X,0
D,ALL,UX,0
NSEL,S,LOC,Z,0
D,ALL,UZ,0
ALLSEL
{transverse_constraints}
NSEL,S,LOC,X,{L}
F,ALL,FX,{SIGMA*W*H/4}
ALLSEL
/SOLU
ANTYPE,STATIC
SOLVE
FINISH
/POST1
SET,LAST
*CFOPEN,'{ap(raw)}','csv'
{chr(10).join(extract)}
*CFCLOS
/EXIT,NOSAVE
"""
    run_apdl(CASE,apdl); got=numeric_rows(raw,["angle_deg","ux_m"]); rows=[]
    for r in got:
        et=theory(r["angle_deg"]); efe=SIGMA/(r["ux_m"]/L); rows.append({"angle_deg":r["angle_deg"],"effective_modulus_pa":efe,"theory_modulus_pa":et,"relative_error":rel_error(efe,et),"axial_strain":r["ux_m"]/L})
    checks={"three_orientations":len(rows)==3,"0deg_error_below_3pct":rows[0]["relative_error"]<.03,"45deg_error_below_5pct":rows[1]["relative_error"]<.05,"90deg_error_below_3pct":rows[2]["relative_error"]<.03,"anisotropy_observed":rows[0]["effective_modulus_pa"]>10*rows[2]["effective_modulus_pa"]}
    data=payload("G","Orthotropic lamina orientation response","3D orthotropic linear elasticity","Static tension with element material axes",{"element":"SOLID185","three_independent_bars":True},{"E1_pa":E1,"E2_pa":E2,"E3_pa":E3,"nu12":NU12,"nu23":NU23,"nu13":NU13,"G12_pa":G12,"G23_pa":G23,"G13_pa":G13,"angles_deg":ANGLES},
      {"orientation_results":rows},{"formula":"1/E(theta)=S11*c^4+S22*s^4+(2*S12+S66)*s^2*c^2"},{"maximum_relative_error":max(r["relative_error"] for r in rows)},checks,[p["input"],p["solver"],p["log"],raw])
    return finish(CASE,data,rows,[([r["angle_deg"] for r in rows],[r["effective_modulus_pa"]/1e9 for r in rows],"MAPDL"),([r["angle_deg"] for r in rows],[r["theory_modulus_pa"]/1e9 for r in rows],"transformed compliance")],("Material angle [deg]","Effective modulus [GPa]"))


if __name__=="__main__": raise SystemExit(main())
