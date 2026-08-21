"""Case K: 12-case Stefan phase-change field dataset."""

from __future__ import annotations

import json, math
import numpy as np
from scipy.optimize import brentq
from scipy.special import erf

from phase_reactive_common import DATA, OUT, base_payload, ensure_dirs, structured_quad_mesh, write_json
from phase_reactive_field_export import save_phase_change


def main() -> int:
    ensure_dirs(); folder = DATA / "phase_change"; folder.mkdir(parents=True, exist_ok=True)
    xs = np.linspace(0.0, 0.08, 101); ys = np.asarray([0.0, 0.001]); coords, conn = structured_quad_mesh(xs, ys)
    times = np.asarray([60.0, 300.0, 900.0, 1800.0]); rho, cp, tm0 = 780.0, 2200.0, 300.0
    parameters=[]; temps=[]; fracs=[]; fronts=[]; globals_f=[]; energy_errors=[]
    for i in range(12):
        latent = 150_000.0 + 6_000.0*i; conductivity = 0.16 + 0.008*i
        tm = tm0 + (i % 4) * 2.0; th = tm + 32.0 + (i % 3)*4.0
        alpha=conductivity/(rho*cp); ste=cp*(th-tm)/latent
        lam=brentq(lambda z:math.sqrt(math.pi)*z*math.exp(z*z)*erf(z)-ste,1e-10,3)
        case_t=[];case_f=[];case_front=[];case_energy=[]
        for t in times:
            front=2*lam*math.sqrt(alpha*t); tx=np.full_like(xs,tm);mask=xs<=front
            tx[mask]=th-(th-tm)*np.asarray([erf(v/(2*math.sqrt(alpha*t))) for v in xs[mask]])/erf(lam)
            fx=(xs<front).astype(float); case_t.append(np.repeat(tx,2));case_f.append(np.repeat(fx,2));case_front.append(front)
            stored=rho*np.trapezoid(cp*(tx-tm)+latent*fx,xs)
            heat_in=2*conductivity*(th-tm)*math.sqrt(t)/(math.sqrt(math.pi*alpha)*erf(lam))
            case_energy.append(abs(stored-heat_in)/heat_in)
        temps.append(case_t);fracs.append(case_f);fronts.append(case_front);globals_f.append(np.mean(case_f,axis=1))
        parameters.append([latent,conductivity,tm,th]);energy_errors.append(case_energy)
    metadata={"dataset":"phase-change Stefan parameter sweep","case_count":12,"solver":"analytical one-phase Stefan",
              "inputs":["latent_heat_J_kg","conductivity_W_mK","melting_temperature_K","wall_temperature_K"],
              "fields":{"temperature":"field[case,time,node]","liquid_fraction":"field[case,time,node]","energy_balance_relative_error":"global[case,time]"},
              "units":{"coordinates":"m","time":"s","temperature":"K","liquid_fraction":"1","interface_position":"m"},
              "solver_version":"SciPy analytical reference","model_settings":{"density_kg_m3":rho,"cp_J_kgK":cp}}
    path=folder/"phase_change_dataset.npz"
    save_phase_change(path,coordinates=coords,connectivity=conn,time=times,temperature=np.asarray(temps),liquid_fraction=np.asarray(fracs),
        velocity_x=np.zeros_like(temps),velocity_y=np.zeros_like(temps),global_quantities={"case_parameters":np.asarray(parameters),
        "interface_position":np.asarray(fronts),"total_liquid_fraction":np.asarray(globals_f),
        "energy_balance_relative_error":np.asarray(energy_errors)},metadata=metadata)
    checks={"case_count_12":len(parameters)==12,"field_shape":np.asarray(temps).shape==(12,4,202),
            "bounded":bool(((np.asarray(fracs)>=0)&(np.asarray(fracs)<=1)).all()),"fronts_monotonic":all(np.all(np.diff(x)>0) for x in fronts),
            "energy_balance_error_lt_15pct":float(np.max(energy_errors))<0.15}
    payload=base_payload("K","Phase-change neural-operator dataset","analytical Stefan parameter sweep")
    payload.update({"dataset":metadata,"checks":checks,"files":[str(path.resolve())],"status":"PASS" if all(checks.values()) else "FAIL"})
    write_json(OUT/"case_k.json",payload);print(payload);return 0 if payload["status"]=="PASS" else 1

if __name__=="__main__":raise SystemExit(main())
