"""Case H: cubic single-crystal directional elastic moduli."""

from __future__ import annotations

import math
from solid_materials_common import *

CASE="single_crystal_elasticity"; C11=168.4e9; C12=121.4e9; C44=75.4e9; SIGMA=50e6; L=.10; W=.01; H=.01
DIRECTIONS={"100":(1.,0.,0.),"110":(1/math.sqrt(2),1/math.sqrt(2),0.),"111":(1/math.sqrt(3),)*3}
DEN=(C11-C12)*(C11+2*C12); S11=(C11+C12)/DEN; S12=-C12/DEN; S44=1/C44; EAX=1/S11; NU=-S12/S11


def dot(a,b): return sum(x*y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def unit(a):
    q=math.sqrt(dot(a,a)); return tuple(x/q for x in a)
def direction_modulus(n):
    q=S11-S12-S44/2; f=n[0]**2*n[1]**2+n[1]**2*n[2]**2+n[2]**2*n[0]**2
    return 1/(S11-2*q*f)


def main()->int:
    p=clean_case(CASE); raw=p["dir"]/"single_crystal_raw.csv"; nodes=[]; elems=[]; systems=[]; ds=[]; forces=[]; gets=[]; nid=1
    for j,(label,n) in enumerate(DIRECTIONS.items()):
        e2=unit(cross((0,0,1),n)) if abs(n[2])<.9 else unit(cross((0,1,0),n)); e3=unit(cross(n,e2)); base=(0,j*.04,0)
        local=[(0,0,0),(L,0,0),(L,W,0),(0,W,0),(0,0,H),(L,0,H),(L,W,H),(0,W,H)]; ids=list(range(nid,nid+8))
        for ii,(x,y,z) in zip(ids,local):
            xyz=tuple(base[k]+x*n[k]+y*e2[k]+z*e3[k] for k in range(3)); nodes.append(f"N,{ii},{xyz[0]},{xyz[1]},{xyz[2]}")
        elems.append("E,"+",".join(map(str,ids)))
        cs=30+j
        systems.append(f"CS,{cs},0,{ids[0]},{ids[1]},{ids[3]}\nNSEL,S,NODE,,{ids[0]},{ids[-1]}\nNROTAT,ALL\nALLSEL")
        ds += [f"D,{ids[0]},ALL,0"]+[f"D,{node},UX,0" for node in (ids[3],ids[4],ids[7])]+[f"D,{ids[3]},UZ,0",f"D,{ids[4]},UY,0"]
        for node in (ids[1],ids[2],ids[5],ids[6]):
            forces += [f"F,{node},FX,{SIGMA*W*H/4}"]
        terms=[]
        for node in (ids[1],ids[2],ids[5],ids[6]):
            for comp,v in zip(("X","Y","Z"),n):
                terms.append(f"*GET,U{node}{comp},NODE,{node},U,{comp}\nUP=UP+U{node}{comp}*{v}/4")
        gets.append(f"UP=0\n{chr(10).join(terms)}\n*VWRITE,{int(label)},UP\n(E22.14,',',E22.14)")
        nid+=8
    apdl=f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,SOLID185
KEYOPT,1,2,3
MP,EX,1,{EAX}
MP,EY,1,{EAX}
MP,EZ,1,{EAX}
MP,PRXY,1,{NU}
MP,PRYZ,1,{NU}
MP,PRXZ,1,{NU}
MP,GXY,1,{C44}
MP,GYZ,1,{C44}
MP,GXZ,1,{C44}
{chr(10).join(nodes)}
TYPE,1
MAT,1
{chr(10).join(elems)}
{chr(10).join(systems)}
{chr(10).join(ds)}
{chr(10).join(forces)}
/SOLU
ANTYPE,STATIC
SOLVE
FINISH
/POST1
SET,LAST
RSYS,0
*CFOPEN,'{ap(raw)}','csv'
{chr(10).join(gets)}
*CFCLOS
/EXIT,NOSAVE
"""
    run_apdl(CASE,apdl); got=numeric_rows(raw,["direction","projected_ux_m"]); rows=[]
    for r in got:
        label=str(round(r["direction"])); n=DIRECTIONS[label]; ef=SIGMA/(r["projected_ux_m"]/L); et=direction_modulus(n)
        rows.append({"direction":label,"effective_modulus_pa":ef,"theory_modulus_pa":et,"relative_error":rel_error(ef,et),"projected_strain":r["projected_ux_m"]/L})
    checks={"three_directions":len(rows)==3,"all_errors_below_3pct":max(r["relative_error"] for r in rows)<.03,"directional_anisotropy_observed":max(r["effective_modulus_pa"] for r in rows)/min(r["effective_modulus_pa"] for r in rows)>2}
    data=payload("H","Cubic single-crystal directional elasticity","Cubic C11/C12/C44 represented by orthotropic elastic constants","Static tension along [100]/[110]/[111]",{"element":"three explicitly oriented SOLID185 parallelepipeds","elements":3},{"C11_pa":C11,"C12_pa":C12,"C44_pa":C44,"directions":list(DIRECTIONS)},
      {"direction_results":rows},{"formula":"1/E(n)=S11-2*(S11-S12-S44/2)*sum(n_i^2*n_j^2)"},{"maximum_relative_error":max(r["relative_error"] for r in rows)},checks,[p["input"],p["solver"],p["log"],raw],["Elastic cubic anisotropy only; crystal plasticity and slip-system evolution are out of scope."])
    return finish(CASE,data,rows,[([1,2,3],[r["effective_modulus_pa"]/1e9 for r in rows],"MAPDL"),([1,2,3],[r["theory_modulus_pa"]/1e9 for r in rows],"cubic compliance")],("Direction index: 1=[100], 2=[110], 3=[111]","Effective modulus [GPa]"))


if __name__=="__main__": raise SystemExit(main())
