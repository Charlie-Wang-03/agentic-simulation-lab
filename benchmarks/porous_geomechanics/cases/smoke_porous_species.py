"""Case E: transient tracer breakthrough through a Fluent porous column."""

from __future__ import annotations

import numpy as np

from fluent_mesh import rectangular_2d
from fluent_smoke_common import read_fluent_ascii_export, svg_xy_plot, write_csv
from porous_geomechanics_common import *

CASE="porous_species";L=1.;H=.1;U=.1;RHO=1.;MU=1e-3;K=1e-7;PHI=.4;DT=.1;STEPS=75;SAMPLE=5

def main()->int:
    p=clean_case(CASE);mesh=p["dir"] / "porous_species.msh";rectangular_2d(mesh,[L*i/120 for i in range(121)],[H*j/8 for j in range(9)],bottom=("bottom-symmetry","symmetry"),top=("top-symmetry","symmetry"))
    try:
        history=[];snapshots=[]
        with fluent_session(dimension=2,processor_count=1,cwd=p["dir"]) as s:
            s.settings.file.read_mesh(file_name=str(mesh));s.settings.setup.general.solver.time="unsteady-2nd-order";s.settings.setup.models.viscous.model="laminar";sp=s.settings.setup.models.species;sp.model.option="species-transport";sp.model.material="mixture-template"
            z=s.settings.setup.cell_zone_conditions.fluid["fluid"].porous_zone;z.porous=True;z.porosity.value=PHI;z.viscous_resistance[0].value=1/K;z.viscous_resistance[1].value=1/K
            inlet=s.settings.setup.boundary_conditions.velocity_inlet["inlet"];inlet.momentum.velocity_magnitude.value=U;yin=inlet.species.species_mass_fraction;yin["h2o"].value=0.;yin["o2"].value=1.
            s.settings.solution.run_calculation.parameters.time_step_size=DT;s.settings.solution.initialization.standard_initialize();yin["o2"].value=0.;yin["h2o"].value=1.
            allowed=list(s.fields.field_data.scalar_fields.allowed_values());h2="h2o" if "h2o" in allowed else next((x for x in allowed if "h2o" in x.lower() and ("mass" in x.lower() or "fraction" in x.lower())),None);o2="o2" if "o2" in allowed else next((x for x in allowed if "o2" in x.lower() and ("mass" in x.lower() or "fraction" in x.lower())),None)
            n2="n2" if "n2" in allowed else None
            if not h2 or not o2 or not n2:raise RuntimeError(f"Species scalar fields not found; available={allowed}")
            for step in range(SAMPLE,STEPS+1,SAMPLE):
                s.settings.solution.run_calculation.dual_time_iterate(time_step_count=SAMPLE,max_iter_per_step=15);raw=p["dir"] / f"sample_{step:04d}.csv";s.settings.file.export.ascii(file_name=str(raw),surface_name_list=["outlet"],delimiter="comma",quantities=["x-coordinate","y-coordinate",h2,o2,n2,"x-velocity","pressure"],location="node");got=read_fluent_ascii_export(raw);yh=float(np.mean([r[h2] for r in got]));yo=float(np.mean([r[o2] for r in got]));yn=float(np.mean([r[n2] for r in got]));history.append({"time_s":step*DT,"outlet_tracer_mass_fraction":yh,"outlet_o2_mass_fraction":yo,"outlet_n2_mass_fraction":yn,"sum_y":yh+yo+yn});snapshots.append(str(raw.resolve()))
            s.settings.file.write_case_data(file_name=str(p["dir"] / "porous_species.cas.h5"))
        times=np.asarray([r["time_s"] for r in history]);conc=np.asarray([r["outlet_tracer_mass_fraction"] for r in history]);idx=np.flatnonzero(conc>=.5);t50=float(times[idx[0]]) if len(idx) else float("inf");expected=PHI*L/U
        checks={"species_bounded":float(conc.min())>=-1e-6 and float(conc.max())<=1+1e-6,"species_sum_error_lt_1e_4":max(abs(r["sum_y"]-1) for r in history)<1e-4,"breakthrough_monotonic":bool(np.all(np.diff(conc)>=-2e-3)),"front_reaches_outlet":conc[-1]>.8,"breakthrough_time_within_35pct":relative_error(t50,expected)<.35}
        csvp=write_csv(p["dir"] / "breakthrough_curve.csv",list(history[0]),history);svg=svg_xy_plot(p["dir"] / "breakthrough_curve.svg",[(r["time_s"],r["outlet_tracer_mass_fraction"]) for r in history],title="Case E: porous tracer breakthrough",xlabel="time (s)",ylabel="outlet tracer mass fraction",reference=[(0.,0.),(expected,0.5),(STEPS*DT,1.)])
        payload=status_payload("E","Porous-media transient species transport","PASS" if all(checks.values()) else "FAIL",solver="Ansys Fluent",material_model="porous Species Transport",permeability_m2=K,porosity=PHI,mesh={"nx":120,"ny":8},time={"dt_s":DT,"steps":STEPS},results={"breakthrough_time_50pct_s":t50,"expected_pore_volume_residence_time_s":expected,"history":history},errors={"breakthrough_time_relative":relative_error(t50,expected)},checks=checks,files=[str(x.resolve()) for x in (mesh,csvp,svg,p["dir"] / "porous_species.cas.h5")]+snapshots)
    except Exception as exc:
        status,error=classify_solver_error(exc);payload=status_payload("E","Porous-media transient species transport",status,error=error,files=[str(mesh.resolve())])
    write_json(p["result"],payload);print(payload);return 0 if payload["status"] in ("PASS","BLOCKED BY CURRENT LICENSE CONTEXT") else 1

if __name__=="__main__":raise SystemExit(main())
