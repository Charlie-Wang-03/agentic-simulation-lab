"""Case D: heated Fluent porous channel with a global energy balance."""

from __future__ import annotations

import numpy as np

from fluent_mesh import rectangular_2d
from fluent_smoke_common import read_fluent_ascii_export, svg_field_map
from porous_field_export import export_fluent_rows
from porous_geomechanics_common import *

CASE="porous_heat_transfer";L=1.;H=.1;U=.005;RHO=1000.;MU=1e-3;CP=4180.;KF=.6;K=1e-8;PHI=.35;TIN=300.;QW=1000.

def main()->int:
    p=clean_case(CASE);mesh=p["dir"] / "porous_heat.msh";rectangular_2d(mesh,[L*i/100 for i in range(101)],[H*j/12 for j in range(13)])
    try:
        with fluent_session(dimension=2,processor_count=1,cwd=p["dir"]) as s:
            s.settings.file.read_mesh(file_name=str(mesh));s.settings.setup.models.viscous.model="laminar";s.settings.setup.models.energy.enabled=True
            f=s.settings.setup.materials.fluid["air"];f.density.value=RHO;f.viscosity.value=MU;f.specific_heat.value=CP;f.thermal_conductivity.value=KF
            z=s.settings.setup.cell_zone_conditions.fluid["fluid"].porous_zone;z.porous=True;z.porosity.value=PHI;z.viscous_resistance[0].value=1/K;z.viscous_resistance[1].value=1/K;z.equib_thermal="Equilibrium"
            inlet=s.settings.setup.boundary_conditions.velocity_inlet["inlet"];inlet.momentum.velocity_magnitude.value=U;inlet.thermal.temperature.value=TIN
            s.settings.setup.boundary_conditions.pressure_outlet["outlet"].thermal.backflow_total_temperature.value=TIN
            hot=s.settings.setup.boundary_conditions.wall["top-wall"];hot.thermal.thermal_condition="Heat Flux";hot.thermal.heat_flux.value=QW
            cold=s.settings.setup.boundary_conditions.wall["bottom-wall"];cold.thermal.thermal_condition="Heat Flux";cold.thermal.heat_flux.value=0.
            s.settings.solution.initialization.standard_initialize();s.settings.solution.run_calculation.iterate(iter_count=1000)
            integ=s.settings.results.report.surface_integrals;mdot=abs(float(integ.get_mass_flow_rate(surface_names=["outlet"])["outlet"]));tin=float(integ.get_mass_weighted_avg(surface_names=["inlet"],report_of="temperature")["inlet"]);tout=float(integ.get_mass_weighted_avg(surface_names=["outlet"],report_of="temperature")["outlet"])
            raw=p["dir"] / "porous_heat_field.csv";s.settings.file.export.ascii(file_name=str(raw),surface_name_list=["interior","inlet","outlet","top-wall"],delimiter="comma",quantities=["x-coordinate","y-coordinate","pressure","x-velocity","y-velocity","temperature"],location="node");s.settings.file.write_case_data(file_name=str(p["dir"] / "porous_heat.cas.h5"))
        rows=read_fluent_ascii_export(raw);q_enthalpy=mdot*CP*(tout-tin);q_input=QW*L;imbalance=relative_error(q_enthalpy,q_input)
        checks={"temperature_rises":tout>tin,"heat_input_positive":q_enthalpy>0,"energy_balance_lt_8pct":imbalance<.08,"temperature_finite":all(np.isfinite(r["temperature"]) for r in rows)}
        npz=export_fluent_rows(p["dir"] / "porous_heat_field.npz",rows,metadata={"case":"D","solver":"Fluent 261","model":"thermal-equilibrium porous media","parameters":{"K_m2":K,"porosity":PHI,"wall_heat_flux_W_m2":QW},"units":{"coordinates":"m","pressure":"Pa","velocity":"m/s","temperature":"K"}});svg=svg_field_map(p["dir"] / "temperature.svg",[(r["x-coordinate"],r["y-coordinate"],r["temperature"]) for r in rows],title="Case D: porous channel temperature")
        payload=status_payload("D","Porous-media heat transfer","PASS" if all(checks.values()) else "FAIL",solver="Ansys Fluent",material_model="local thermal equilibrium porous model",permeability_m2=K,porosity=PHI,fluid={"density_kg_m3":RHO,"viscosity_pa_s":MU,"cp_J_kgK":CP,"conductivity_W_mK":KF},mesh={"nx":100,"ny":12},results={"mass_flow_kg_m_s":mdot,"inlet_temperature_K":tin,"outlet_temperature_K":tout,"enthalpy_gain_W_m":q_enthalpy,"heat_input_W_m":q_input},errors={"energy_imbalance_relative":imbalance},checks=checks,files=[str(x.resolve()) for x in (mesh,raw,npz,svg,p["dir"] / "porous_heat.cas.h5")])
    except Exception as exc:
        status,error=classify_solver_error(exc);payload=status_payload("D","Porous-media heat transfer",status,error=error,files=[str(mesh.resolve())])
    write_json(p["result"],payload);print(payload);return 0 if payload["status"] in ("PASS","BLOCKED BY CURRENT LICENSE CONTEXT") else 1

if __name__=="__main__":raise SystemExit(main())
