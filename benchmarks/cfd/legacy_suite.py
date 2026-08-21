"""Run Cases G-L and the independent dataset validator in order."""
from __future__ import annotations
import subprocess,sys,time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SCRIPTS=[
 "smoke_fluent_cavity.py","smoke_fluent_cylinder_unsteady.py",
 "smoke_fluent_backward_step.py","smoke_fluent_airfoil.py",
 "smoke_fluent_mesh_sensitivity.py","smoke_fluent_parametric_dataset.py",
 "validate_fluent_dataset.py",
]
def main()->int:
    results=[]
    for script in SCRIPTS:
        start=time.time(); log=ROOT/"logs"/f"suite_{Path(script).stem}.log"
        with log.open("w",encoding="utf-8") as stream:
            p=subprocess.run([sys.executable,str(ROOT/script)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=False,timeout=1800)
        results.append((script,p.returncode,time.time()-start,str(log)))
        print(f"{script}: {'PASS' if p.returncode==0 else 'FAIL'} ({results[-1][2]:.1f}s), log={log}")
        if p.returncode: return p.returncode
    return 0
if __name__=="__main__": raise SystemExit(main())
