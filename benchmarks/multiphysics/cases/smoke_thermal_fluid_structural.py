"""Case F: sequential Fluent CHT temperature field to MAPDL structural response."""
from __future__ import annotations
import numpy as np
from fluent_smoke_common import OUT,read_fluent_ascii_export,rel_error
from multiphysics_common import mapdl_session,multiphysics_processes,wait_for_process_cleanup,write_json

CASE="thermal_fluid_structural"; SOURCE=OUT/"cht_fluent_raw.csv";L=.2;W=.01;H=.01;E=70e9;NU=.33;ALPHA=23e-6;TREF_K=300.

def main()->int:
    before=multiphysics_processes();payload={"case":CASE,"sequence":["Fluent flow","CHT","solid temperature mapping","MAPDL structural"]}
    try:
        rows=read_fluent_ascii_export(SOURCE);solid=[r for r in rows if r["y-coordinate"]>=.02-1e-10]
        buckets={}
        for r in solid:buckets.setdefault(round(r["x-coordinate"],10),[]).append(r["temperature"])
        xs=np.asarray(sorted(buckets));ts=np.asarray([np.mean(buckets[x]) for x in xs]);run=OUT/CASE
        with mapdl_session(working_dir=run/"mapdl") as m:
            m.clear();m.prep7();m.et(1,185);m.mp("EX",1,E);m.mp("NUXY",1,NU);m.mp("ALPX",1,ALPHA);m.tref(TREF_K-273.15);m.block(0,L,0,W,0,H);m.esize(.01);m.vmesh("ALL")
            node_ids=np.asarray(m.mesh.nnum,dtype=int);coords=np.asarray(m.mesh.nodes)
            mapped_k=np.interp(coords[:,0],xs,ts)
            for node,temp_k in zip(node_ids,mapped_k):m.bf(int(node),"TEMP",float(temp_k-273.15))
            left=node_ids[np.isclose(coords[:,0],0)];right=node_ids[np.isclose(coords[:,0],L)]
            for node in left:m.d(int(node),"ALL",0)
            for node in right:m.d(int(node),"UX",0)
            m.finish();m.slashsolu();m.antype("STATIC");m.solve();m.finish();m.post1();m.set("LAST")
            disp=np.asarray(m.post_processing.nodal_displacement("ALL"),dtype=float);eqv=np.asarray(m.post_processing.nodal_eqv_stress(),dtype=float)
            max_disp=float(np.nanmax(np.linalg.norm(disp,axis=1)));max_stress=float(np.nanmax(eqv));m.save(str(run/"mapdl"/"thermal_structural.db"))
        mean_dt=float(mapped_k.mean()-TREF_K);max_dt=float(np.max(np.abs(mapped_k-TREF_K)));theory_free=ALPHA*mean_dt*L;theory_stress=E*ALPHA*max_dt
        checks={"source_case_actual":SOURCE.is_file(),"temperature_gradient_nonzero":float(ts.max()-ts.min())>1,"all_nodes_mapped":len(mapped_k)==len(node_ids),"mapped_temperatures_finite":bool(np.isfinite(mapped_k).all()),"thermal_displacement_nonzero":max_disp>0,"thermal_stress_nonzero":max_stress>0,"stress_order_sane":.05<max_stress/theory_stress<5}
        remaining=wait_for_process_cleanup(before);checks["clean_shutdown"]=not remaining
        payload.update({"source":{"case":"Case A Fluent native CHT","file":str(SOURCE.resolve()),"solid_temperature_range_K":[float(ts.min()),float(ts.max())],"mean_mapped_temperature_K":float(mapped_k.mean())},"mapping":{"fluid_solid_field_nodes":len(solid),"structural_nodes":len(node_ids),"method":"1-D axial interpolation; domains kept distinct"},"results":{"temperature_gradient_K":float(ts.max()-ts.min()),"max_thermal_displacement_m":max_disp,"max_equivalent_stress_Pa":max_stress},"sanity":{"free_expansion_scale_m":theory_free,"fully_constrained_stress_scale_Pa":theory_stress,"formulae":["dL=alpha*dT*L","sigma=E*alpha*dT"]},"checks":checks,"status":"PASS" if all(checks.values()) else "FAIL","residual_processes":remaining})
    except Exception as e:payload.update({"status":"FAIL","error":f"{type(e).__name__}: {e}","residual_processes":wait_for_process_cleanup(before)})
    write_json(OUT/f"{CASE}.json",payload);print(payload);return 0 if payload["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
