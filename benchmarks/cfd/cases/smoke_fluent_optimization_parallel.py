"""Case S: nine-point aerodynamic search and 1/2/4-core Fluent comparison."""
from __future__ import annotations
import json,math,time
import numpy as np
from fluent_mesh import rectangular_2d
from fluent_smoke_common import OUT,base_payload,clean_case,fluent_session,read_fluent_ascii_export,svg_xy_plot,write_csv,write_json
from smoke_fluent_airfoil import solve_aoa
CASE="fluent_optimization_parallel";AOA_ALL=(-5,-2,0,2,5,7,10,12,15);NEW=(-2,2,7,12,15)

def parallel_run(mesh,cores):
    raw=OUT/f"{CASE}_{cores}core_raw.csv";start=time.perf_counter()
    with fluent_session(dimension=2,processor_count=cores,cwd=OUT) as s:
        s.settings.file.read_mesh(file_name=str(mesh));s.settings.setup.models.viscous.model="laminar";air=s.settings.setup.materials.fluid["air"];air.density.value=1.;air.viscosity.value=.01;lid=s.settings.setup.boundary_conditions.wall["lid"];lid.momentum.wall_motion="Moving Wall";lid.momentum.velocity_spec="Components";lid.momentum.velocity_components[0].value=1.;lid.momentum.velocity_components[1].value=0.;s.settings.solution.initialization.hybrid_initialize();s.settings.solution.run_calculation.iterate(iter_count=400);iters=None
        if hasattr(s,"get_solver_iteration_count"):
            try:iters=int(s.get_solver_iteration_count())
            except Exception:pass
        s.settings.file.export.ascii(file_name=str(raw),surface_name_list=["interior"],delimiter="comma",quantities=["x-coordinate","y-coordinate","x-velocity","y-velocity","pressure"],location="node")
    wall=time.perf_counter()-start;rows=read_fluent_ascii_export(raw);r=min(rows,key=lambda x:(x["x-coordinate"]-.5)**2+(x["y-coordinate"]-.5)**2)
    return {"cores":cores,"wall_clock_s":wall,"iterations_requested":400,"iterations_completed":iters,"center_u_m_s":r["x-velocity"],"center_v_m_s":r["y-velocity"],"center_pressure_pa":r["pressure"],"raw":raw}

def main()->int:
    clean_case(CASE);payload=base_payload(CASE,"Case S: parameter optimization and parallel Fluent smoke")
    try:
        old=json.loads((OUT/"fluent_airfoil.json").read_text(encoding="utf-8"))["results"]["polar"];polar={int(x["aoa_deg"]):{"aoa_deg":int(x["aoa_deg"]),"cl":x["cl"],"cd":x["cd"],"cl_over_cd":x["cl_over_cd"],"source":"Case J reused"} for x in old}
        for a in NEW:
            r=solve_aoa(a);polar[a]={"aoa_deg":a,"cl":r["cl"],"cd":r["cd"],"cl_over_cd":r["ld"],"source":"Case S new Fluent run"}
        table=[polar[a] for a in AOA_ALL];valid=[x for x in table if x["cd"]>0 and math.isfinite(x["cl_over_cd"])];best=max(valid,key=lambda x:x["cl_over_cd"]);ocsv=write_csv(OUT/f"{CASE}_optimization.csv",list(table[0]),table);osvg=svg_xy_plot(OUT/f"{CASE}_objective.svg",[(x["aoa_deg"],x["cl_over_cd"]) for x in table],title="Case S1: NACA 0012 parameter search",xlabel="AoA (deg)",ylabel="Cl/Cd")
        mesh=OUT/f"{CASE}_parallel.msh";n=40;c=[.5*(1-math.cos(math.pi*i/n)) for i in range(n+1)];mstats=rectangular_2d(mesh,c,c,left=("left-wall","wall"),right=("right-wall","wall"),bottom=("bottom-wall","wall"),top=("lid","wall"));runs=[];errors=[]
        for cores in (1,2,4):
            try:runs.append(parallel_run(mesh,cores))
            except Exception as exc:errors.append({"cores":cores,"error":f"{type(exc).__name__}: {exc}"})
        base=runs[0];comparison=[]
        for r in runs:
            comparison.append({k:v for k,v in r.items() if k!="raw"}|{"speedup_vs_1core":base["wall_clock_s"]/r["wall_clock_s"],"center_u_relative_difference":abs(r["center_u_m_s"]-base["center_u_m_s"])/max(abs(base["center_u_m_s"]),1e-30)})
        pcsv=write_csv(OUT/f"{CASE}_parallel.csv",list(comparison[0]),comparison);psvg=svg_xy_plot(OUT/f"{CASE}_parallel.svg",[(x["cores"],x["wall_clock_s"]) for x in comparison],title="Case S2: Fluent parallel wall clock",xlabel="processor count",ylabel="wall clock (s)")
        checks={"optimization_has_9_cases":len(table)==9,"five_new_fluent_runs":sum(x["source"].startswith("Case S") for x in table)==5,"best_objective_positive":best["cl_over_cd"]>0,"at_least_two_parallel_counts":len(runs)>=2,"parallel_result_consistency":max(x["center_u_relative_difference"] for x in comparison)<.01,"finite_wall_times":all(math.isfinite(x["wall_clock_s"]) and x["wall_clock_s"]>0 for x in comparison)}
        payload.update({"optimization":{"parameters":{"aoa_deg":list(AOA_ALL)},"objective":"maximize Cl/Cd","results":table,"best":best},"parallel":{"benchmark":"Re=100 lid-driven cavity","mesh":mstats,"requested_cores":[1,2,4],"successful_runs":comparison,"unavailable_runs":errors,"timing_scope":"PyFluent launch + initialize + solve + ASCII export","iteration_note":"iterations_completed from PyFluent when available; otherwise requested count retained"},"checks":checks,"status":"PASS" if all(checks.values()) else "FAIL","files":[str(x.resolve()) for x in [ocsv,osvg,mesh,pcsv,psvg,*[r['raw'] for r in runs]]]})
    except Exception as exc:payload.update({"status":"FAIL","error":f"{type(exc).__name__}: {exc}"})
    write_json(OUT/f"{CASE}.json",payload);print(payload);return 0 if payload["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
