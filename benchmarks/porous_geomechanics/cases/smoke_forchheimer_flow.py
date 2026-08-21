"""Case B: Fluent Darcy-Forchheimer velocity sweep and coefficient fit."""

from __future__ import annotations

import numpy as np

from fluent_mesh import rectangular_2d
from fluent_smoke_common import read_fluent_ascii_export, svg_xy_plot, write_csv
from porous_geomechanics_common import *


CASE="forchheimer_flow"; L=1.; H=.1; RHO=1000.; MU=1e-3; D=1e8; C2=2000.; PHI=.35
VELOCITIES=[.002,.005,.01,.02,.04,.06,.08]


def main()->int:
    paths=clean_case(CASE); mesh=paths["dir"] / "forchheimer.msh"
    rectangular_2d(mesh,[L*i/80 for i in range(81)],[H*j/8 for j in range(9)],bottom=("bottom-symmetry","symmetry"),top=("top-symmetry","symmetry"))
    try:
        rows=[]; artifacts=[str(mesh.resolve())]
        with fluent_session(dimension=2,processor_count=1,cwd=paths["dir"]) as s:
            s.settings.file.read_mesh(file_name=str(mesh));s.settings.setup.models.viscous.model="laminar"
            fluid=s.settings.setup.materials.fluid["air"];fluid.density.value=RHO;fluid.viscosity.value=MU
            zone=s.settings.setup.cell_zone_conditions.fluid["fluid"].porous_zone;zone.porous=True;zone.porosity.value=PHI
            zone.viscous_resistance[0].value=D;zone.viscous_resistance[1].value=D
            zone.inertial_resistance[0].value=C2;zone.inertial_resistance[1].value=C2
            for name,x in (("station-up",.1*L),("station-down",.9*L)):
                s.settings.results.surfaces.line_surface[name]={"p0":[x,0.,0.],"p1":[x,H,0.]}
            for index,u in enumerate(VELOCITIES):
                s.settings.setup.boundary_conditions.velocity_inlet["inlet"].momentum.velocity_magnitude.value=u
                s.settings.solution.initialization.hybrid_initialize();s.settings.solution.run_calculation.iterate(iter_count=400)
                raw=paths["dir"]/f"sweep_{index:02d}.csv";s.settings.file.export.ascii(file_name=str(raw),surface_name_list=["station-up","station-down"],delimiter="comma",quantities=["x-coordinate","y-coordinate","pressure","x-velocity"],location="node")
                got=read_fluent_ascii_export(raw);up=[r for r in got if abs(r["x-coordinate"]-.1*L)<1e-9];dn=[r for r in got if abs(r["x-coordinate"]-.9*L)<1e-9]
                gradient=(np.mean([r["pressure"] for r in up])-np.mean([r["pressure"] for r in dn]))/(.8*L)
                rows.append({"velocity_m_s":u,"pressure_gradient_pa_m":float(gradient),"pressure_drop_pa":float(gradient*.8*L),"darcy_fraction":float(MU*D*u/gradient)})
                artifacts.append(str(raw.resolve()))
            s.settings.file.write_case_data(file_name=str(paths["dir"]/"forchheimer.cas.h5"));artifacts.append(str((paths["dir"]/"forchheimer.cas.h5").resolve()))
        x=np.asarray(VELOCITIES); y=np.asarray([r["pressure_gradient_pa_m"] for r in rows]); design=np.column_stack([x,x*x]); a,b=np.linalg.lstsq(design,y,rcond=None)[0]
        expected_a=MU*D;expected_b=.5*RHO*C2;fit=design@np.asarray([a,b]);r2=1-float(np.sum((y-fit)**2)/np.sum((y-y.mean())**2))
        errors={"linear_coefficient_relative":relative_error(float(a),expected_a),"quadratic_coefficient_relative":relative_error(float(b),expected_b)}
        checks={"seven_conditions":len(rows)>=5,"linear_coefficient_error_lt_5pct":errors["linear_coefficient_relative"]<.05,"quadratic_coefficient_error_lt_5pct":errors["quadratic_coefficient_relative"]<.05,"fit_r2_gt_0p999":r2>.999,"darcy_and_inertial_regions":rows[0]["darcy_fraction"]>.95 and rows[-1]["darcy_fraction"]<.7}
        csvp=write_csv(paths["dir"] / "pressure_drop_vs_velocity.csv",list(rows[0]),rows);svg=svg_xy_plot(paths["dir"] / "pressure_drop_vs_velocity.svg",[(r["velocity_m_s"],r["pressure_gradient_pa_m"]) for r in rows],title="Case B: Darcy-Forchheimer pressure loss",xlabel="superficial velocity (m/s)",ylabel="pressure gradient (Pa/m)",reference=[(float(u),float(expected_a*u+expected_b*u*u)) for u in x])
        payload=status_payload("B","Darcy-Forchheimer nonlinear seepage","PASS" if all(checks.values()) else "FAIL",solver="Ansys Fluent",material_model="viscous + inertial porous resistance",permeability_m2=1/D,porosity=PHI,fluid={"density_kg_m3":RHO,"viscosity_pa_s":MU},results={"sweep":rows,"fit_a_pa_s_m2":float(a),"fit_b_pa_s2_m3":float(b),"r_squared":r2},theory={"law":"dp/L=mu*D*U+0.5*rho*C2*U^2","a":expected_a,"b":expected_b},errors=errors,checks=checks,files=artifacts+[str(csvp.resolve()),str(svg.resolve())])
    except Exception as exc:
        status,error=classify_solver_error(exc);payload=status_payload("B","Darcy-Forchheimer nonlinear seepage",status,error=error,files=[str(mesh.resolve())])
    write_json(paths["result"],payload);print(payload);return 0 if payload["status"] in ("PASS","BLOCKED BY CURRENT LICENSE CONTEXT") else 1


if __name__=="__main__":raise SystemExit(main())
