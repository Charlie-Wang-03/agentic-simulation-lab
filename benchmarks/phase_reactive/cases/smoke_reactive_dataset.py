"""Case L: 12-case lumped methane-reaction transport field dataset."""

from __future__ import annotations

import numpy as np

from phase_reactive_common import DATA, OUT, base_payload, ensure_dirs, structured_quad_mesh, write_json
from phase_reactive_field_export import save_reactive_flow


def main()->int:
    ensure_dirs();folder=DATA/"reactive_flow";folder.mkdir(parents=True,exist_ok=True)
    xs=np.linspace(0,0.2,101);ys=np.linspace(0,0.02,11);coords,conn=structured_quad_mesh(xs,ys)
    species={k:[] for k in ("fuel_ch4_lumped","products_co2_h2o_lumped","inert_n2")}
    ux=[];uy=[];pressure=[];temperature=[];rates=[];heat=[];parameters=[]
    for i in range(12):
        velocity=.08+.015*i;tin=850.+20*(i%4);fuel=.035+.004*(i%5);k=.35+.07*i;inert=.72
        x=coords[:,0];yf=fuel*np.exp(-k*x/velocity);consumed=fuel-yf;yp=consumed;yn=np.full_like(x,1.-fuel)
        # Lumped mass-conserving one-step chemistry; product represents CO2+H2O together.
        temp=tin+consumed*12_000.;rate=k*yf;hrr=rate*50e6
        species["fuel_ch4_lumped"].append(yf);species["products_co2_h2o_lumped"].append(yp);species["inert_n2"].append(yn)
        ux.append(np.full_like(x,velocity));uy.append(np.zeros_like(x));pressure.append(101325.-40*x/0.2)
        temperature.append(temp);rates.append(rate);heat.append(hrr);parameters.append([velocity,tin,fuel,k])
    metadata={"dataset":"reactive-flow lumped methane parameter sweep","case_count":12,
      "solver":"analytical first-order plug-flow transport","species_names":["fuel_ch4_lumped","products_co2_h2o_lumped","inert_n2"],
      "chemical_mechanism":{"reaction":"CH4_lumped -> CO2+H2O_lumped","rate_law":"r=k*Y_fuel","scope":"mass-conserving reduced chemistry, not Fluent"},
      "inputs":["inlet_velocity_m_s","inlet_temperature_K","fuel_mass_fraction","rate_constant_1_s"],
      "fields":"field[case,node]","units":{"coordinates":"m","velocity":"m/s","pressure":"Pa","temperature":"K","mass_fraction":"1","reaction_rate":"1/s","heat_release_rate":"W/kg"},
      "solver_version":"NumPy analytical reference","model_settings":{"heat_of_reaction_J_kg_fuel":50e6,"effective_cp_J_kgK":50e6/12_000.}}
    path=folder/"reactive_flow_dataset.npz"
    save_reactive_flow(path,coordinates=coords,connectivity=conn,velocity_x=np.asarray(ux),velocity_y=np.asarray(uy),
      pressure=np.asarray(pressure),temperature=np.asarray(temperature),species={k:np.asarray(v) for k,v in species.items()},
      reaction_rate=np.asarray(rates),heat_release_rate=np.asarray(heat),metadata=metadata)
    # Add numeric case parameters without weakening the canonical writer.
    with np.load(path,allow_pickle=False) as d: arrays={k:d[k] for k in d.files}
    arrays["case_parameters"]=np.asarray(parameters);np.savez_compressed(path,**arrays)
    sums=sum(np.asarray(v) for v in species.values())
    checks={"case_count_12":len(parameters)==12,"field_shape":np.asarray(temperature).shape==(12,1111),
            "species_bounded":all(bool(((np.asarray(v)>=0)&(np.asarray(v)<=1)).all()) for v in species.values()),
            "species_sum_error_lt_1e-12":float(np.max(np.abs(sums-1)))<1e-12,"reaction_finite":bool(np.isfinite(rates).all()),
            "heat_release_temperature_identity":all(bool(np.allclose(np.asarray(temperature)[n]-parameters[n][1],
                (parameters[n][2]-np.asarray(species["fuel_ch4_lumped"])[n])*50e6/(50e6/12_000.),rtol=1e-12,atol=1e-10)) for n in range(12))}
    payload=base_payload("L","Reactive-flow neural-operator dataset","analytical first-order reacting transport")
    payload.update({"dataset":metadata,"checks":checks,"files":[str(path.resolve())],"status":"PASS" if all(checks.values()) else "FAIL"})
    write_json(OUT/"case_l.json",payload);print(payload);return 0 if payload["status"]=="PASS" else 1

if __name__=="__main__":raise SystemExit(main())
