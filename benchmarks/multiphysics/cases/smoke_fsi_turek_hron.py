"""Case E: official Turek-Hron FSI2 startup smoke (formal benchmark needs 35 s)."""
from __future__ import annotations
import csv,re,sys,shutil
import numpy as np
from ansys.systemcoupling.core.participant.mapdl import MapdlSystemCouplingInterface
from fluent_smoke_common import fluent_session
from multiphysics_common import OUT,mapdl_session,multiphysics_processes,system_coupling_session,wait_for_process_cleanup,write_json

CASE="fsi_turek_hron"; ASSETS=OUT/"official_assets"

def continue_existing(end_time:float)->int:
    """Restart an externally-managed run after the original Python process exited."""
    before=multiphysics_processes();run=OUT/CASE;syc_dir=run/"system-coupling"/"SyC"
    restart_steps=sorted(int(p.stem.replace("Restart_step","")) for p in syc_dir.glob("Restart_step*.h5"))
    step=restart_steps[-1];latest=run/"fluent"/f"fluent-fsi2-0-{step:05d}.cas.h5"
    evidence={"restart_step":step,"restart_time_s":step*.01,"requested_end_time_s":end_time,"fluent_case":str(latest.resolve()),"mapdl_database":str((run/"mapdl"/"file.db").resolve())}
    try:
        backup=run/"restart_safety_backup"
        backup.mkdir(exist_ok=True)
        for source in list((run/"mapdl").glob("file.*"))+[latest,latest.with_suffix("").with_suffix(".dat.h5")]:
            if source.is_file() and not (backup/source.name).exists():shutil.copy2(source,backup/source.name)
        with mapdl_session(working_dir=run/"mapdl") as m, fluent_session(dimension=3,processor_count=1,cwd=run/"fluent",start_transcript=True) as f, system_coupling_session(working_dir=run/"system-coupling") as syc:
            m.resume(str(run/"mapdl"/"file.db"));m.slashsolu();m.antype(4,"REST");m.time(step*.01)
            f.settings.file.read_case_data(file_name=str(latest))
            syc.case.open(file_path=str(syc_dir),coupling_step=step)
            syc.setup.solution_control.end_time=f"{end_time} [s]"
            syc.setup.output_control.option="EveryStep";syc.setup.output_control.generate_csv_chart_output=True
            # case.open restores the System Coupling data model. Reattach the two
            # fresh participant sessions under their persisted internal names.
            provider=getattr(syc,"_Session__injected_cmd_map")
            manager=provider.participant_manager
            setattr(manager,"_ParticipantManager__participants",{
                "FLUENT-1":f.system_coupling,
                "MAPDL-2":MapdlSystemCouplingInterface(m),
            })
            syc.solution.solve()
        remaining=wait_for_process_cleanup(before);evidence.update({"status":"PASS","residual_processes":remaining})
    except Exception as e:
        evidence.update({"status":"FAIL","error":f"{type(e).__name__}: {e}","residual_processes":wait_for_process_cleanup(before)})
    write_json(run/"continuation_last.json",evidence);print(evidence);return 0 if evidence["status"]=="PASS" else 1

def postprocess_existing()->int:
    run=OUT/CASE;d=run/"system-coupling"/"SyC";log=(d/"scLog.scl").read_text(encoding="utf-8",errors="replace")
    mapped=[float(v) for pair in re.findall(r"Mapped (?:Area|Elements|Nodes) \[%\].*?\|\s*([0-9.]+)\s+([0-9.]+)",log) for v in pair]
    with (d/"Interface-1.csv").open(newline="",encoding="utf-8-sig") as s:rows=list(csv.DictReader(s))
    last={}
    for row in rows:last[int(row["Step"])]=row
    keys=list(rows[0]);dy=next(k for k in keys if k.startswith("displacement (Weighted Average): MAPDL") and k.endswith(" y"));fx=next(k for k in keys if k.startswith("Force (Sum): FLUENT") and k.endswith(" x"));fy=next(k for k in keys if k.startswith("Force (Sum): FLUENT") and k.endswith(" y"))
    hist=[{"step":k,"time_s":float(r["Time"]),"interface_average_y_displacement_m":float(r[dy]),"interface_force_x_N":float(r[fx]),"interface_force_y_N":float(r[fy]),"interface_force_x_N_per_m":float(r[fx])/.01,"interface_force_y_N_per_m":float(r[fy])/.01} for k,r in sorted(last.items())]
    drag_ref=np.loadtxt(ASSETS/"drag_data.csv",delimiter=",");lift_ref=np.loadtxt(ASSETS/"lift_data.csv",delimiter=",")
    continuation={}
    if (run/"continuation_last.json").is_file():
        import json
        continuation=json.loads((run/"continuation_last.json").read_text(encoding="utf-8"))
    actual_end=max(x["time_s"] for x in hist);formal=actual_end>=34.
    checks={"official_assets_used":True,"two_way_transfers":True,"ten_startup_steps":len(hist)==10,"mapping_100_percent":bool(mapped) and min(mapped)>=99.9,"motion_nonzero":max(abs(x["interface_average_y_displacement_m"]) for x in hist)>0,"forces_finite":all(np.isfinite(x["interface_force_x_N"]) and np.isfinite(x["interface_force_y_N"]) for x in hist),"formal_34_35s_window_reached":formal,"beam_tip_history_extracted":False,"frequency_and_amplitude_compared":False,"clean_shutdown":not multiphysics_processes()}
    payload={"case":CASE,"benchmark":"Turek-Hron FSI2","dt_s":.01,"formal_reference_window_s":[34,35],"actual_end_time_s":actual_end,"participants":["FLUENT-1","MAPDL-2"],"interface":"Interface-1","data_transfers":["Force","displacement"],"mapping":{"minimum_percent":min(mapped)},"startup_history":hist,"published_reference":{"quantity_units":"N/m (official 2-D reference; Fluent 0.01 m-depth force is divided by 0.01 m for comparison)","drag_range_N_per_m":[float(drag_ref[:,1].min()),float(drag_ref[:,1].max())],"lift_range_N_per_m":[float(lift_ref[:,1].min()),float(lift_ref[:,1].max())],"time_range_s":[34,35]},"benchmark_metrics":{"beam_tip_x_amplitude_m":None,"beam_tip_y_amplitude_m":None,"drag_range_N_per_m":None,"lift_range_N_per_m":None,"oscillation_frequency_Hz":None,"reference_comparison":None},"restart":{"system_coupling_points":len(list(d.glob("Restart_step*.h5"))),"fluent_autosave_pairs":len(list((run/"fluent").glob("*.dat.h5"))),"last_continuation_attempt":continuation,"next_fix":"Resume MAPDL transient restart state and explicitly align its beginning time to 0.1 s before reattaching the externally managed participant."},"checks":{k:bool(v) for k,v in checks.items()},"status":"PASS" if all(checks.values()) else "FAIL","limitation":"The actual run ends at 0.1 s. The 34-35 s periodic window, beam-tip amplitudes, frequency, and quantitative reference comparison do not exist, so benchmark PASS is not claimed."}
    write_json(OUT/f"{CASE}.json",payload);print(payload);return 1

def main()->int:
    before=multiphysics_processes(); run=OUT/CASE; run.mkdir(parents=True,exist_ok=True)
    payload={"case":CASE,"benchmark":"Turek-Hron FSI2","formal_reference_window_s":[34.0,35.0],"requested_smoke_end_time_s":0.1}
    try:
        with mapdl_session(working_dir=run/"mapdl") as m, fluent_session(dimension=3,processor_count=1,cwd=run/"fluent",start_transcript=False) as f, system_coupling_session(working_dir=run/"system-coupling") as syc:
            m.clear();m.prep7();m.cdread(option="DB",fname=str(ASSETS/"turek_hron_benchmark_solid.cdb"));m.mp("DENS",1,10000);m.mp("EX",1,1.4e6);m.mp("NUXY",1,.4)
            m.slashsolu();m.antype(4);m.nlgeom("on");m.kbc(1);m.eqslv("sparse");m.run("rstsuppress,none");m.dmpoption("emat","no");m.dmpoption("esav","no");m.cmwrite();m.trnopt(tintopt="hht");m.tintp(.1);m.nldiag("cont","iter");m.scopt("NO");m.autots("on");m.nsubst(1,1,1,"OFF");m.time(.1);m.timint("on");m.outres("all","all")
            f.settings.file.read(file_type="mesh",file_name=str(ASSETS/"fluent-fsi2.msh.h5"));f.settings.setup.general.solver.type="pressure-based";f.settings.solution.methods.high_order_term_relaxation.enable=True;f.settings.setup.models.viscous.model="laminar"
            f.settings.setup.materials.fluid["fsi_fluid"]={"density":{"option":"constant","value":1000},"viscosity":{"option":"constant","value":1}}
            f.settings.setup.cell_zone_conditions.fluid["*fluid*"].general.material="fsi_fluid"
            f.settings.setup.named_expressions["u_bar"]={"definition":"1.0 [m/s]"};f.settings.setup.named_expressions["y_bar"]={"definition":"1.0 [m]"};f.settings.setup.named_expressions["u_y"]={"definition":"1.5*u_bar*(4*(y/y_bar)*(0.41-y/y_bar)/(0.41^2))"}
            f.settings.setup.boundary_conditions.velocity_inlet["inlet"].momentum.velocity_magnitude.value="u_y"
            f.settings.solution.methods.discretization_scheme={"mom":"second-order-upwind","pressure":"second-order"};f.settings.solution.initialization.hybrid_initialize();f.settings.solution.run_calculation.iterate(iter_count=200);f.settings.setup.general.solver.time="unsteady-2nd-order"
            f.tui.define.dynamic_mesh.dynamic_mesh("yes","no","no","no","no");f.tui.define.dynamic_mesh.zones.create("fsi","system-coupling")
            for zone,zval in (("back","0.00"),("front","0.01")): f.tui.define.dynamic_mesh.zones.create(zone,"deforming","plane","0.","0.",zval,"0","0","1","no","yes","yes","yes","no","yes","no","yes")
            for zone in ["cylinder","outlet","inlet","channel"]: f.tui.define.dynamic_mesh.zones.create(zone,"stationary")
            f.settings.solution.run_calculation.transient_controls.max_iter_per_time_step=30
            fluid=syc.setup.add_participant(participant_session=f);solid=syc.setup.add_participant(participant_session=m)
            interface=syc.setup.add_interface(side_one_participant=fluid,side_one_regions=["fsi"],side_two_participant=solid,side_two_regions=["FSIN_1"]);transfers=syc.setup.add_fsi_data_transfers(interface=interface);syc.setup.coupling_interface[interface].data_transfer["FORC"].relaxation_factor=.5
            syc.setup.solution_control.time_step_size="0.01 [s]";syc.setup.solution_control.end_time="0.1 [s]";syc.setup.solution_control.maximum_iterations=5;syc.setup.output_control.option="EveryStep";syc.setup.output_control.generate_csv_chart_output=True;syc.solution.solve()
        d=run/"system-coupling"/"SyC";log=(d/"scLog.scl").read_text(encoding="utf-8",errors="replace");mapped=[float(v) for pair in re.findall(r"Mapped (?:Area|Elements|Nodes) \[%\].*?\|\s*([0-9.]+)\s+([0-9.]+)",log) for v in pair]
        with (d/"Interface-1.csv").open(newline="",encoding="utf-8-sig") as s: rows=list(csv.DictReader(s))
        last={};
        for r in rows:last[int(r["Step"])]=r
        keys=list(rows[0]);dy=next(k for k in keys if k.startswith("displacement (Weighted Average): MAPDL") and k.endswith(" y"));fx=next(k for k in keys if k.startswith("Force (Sum): FLUENT") and k.endswith(" x"));fy=next(k for k in keys if k.startswith("Force (Sum): FLUENT") and k.endswith(" y"))
        hist=[{"step":k,"time_s":float(r["Time"]),"beam_interface_y_displacement_m":float(r[dy]),"drag_N":float(r[fx]),"lift_N":float(r[fy])} for k,r in sorted(last.items())]
        # Published reference data supplied by Ansys covers the fully developed 34-35 s window.
        drag_ref=np.loadtxt(ASSETS/"drag_data.csv",delimiter=",");lift_ref=np.loadtxt(ASSETS/"lift_data.csv",delimiter=",")
        formal_reached=max(x["time_s"] for x in hist)>=34.0; remaining=wait_for_process_cleanup(before)
        checks={"official_assets_used":True,"two_way_transfers":len(transfers)==2,"ten_startup_steps":len(hist)==10,"mapping_100_percent":bool(mapped) and min(mapped)>=99.9,"motion_nonzero":max(abs(x["beam_interface_y_displacement_m"]) for x in hist)>0,"forces_finite":all(np.isfinite(x["drag_N"]) and np.isfinite(x["lift_N"]) for x in hist),"formal_34_35s_window_reached":formal_reached,"clean_shutdown":not remaining}
        payload.update({"participants":[fluid,solid],"interface":interface,"data_transfers":list(transfers),"mapping":{"minimum_percent":min(mapped)},"startup_history":hist,"published_reference":{"drag_range_N":[float(drag_ref[:,1].min()),float(drag_ref[:,1].max())],"lift_range_N":[float(lift_ref[:,1].min()),float(lift_ref[:,1].max())],"time_range_s":[34,35]},"checks":{k:bool(v) for k,v in checks.items()},"status":"PASS" if all(checks.values()) else "FAIL","limitation":None if formal_reached else "Actual 0.1 s startup co-simulation passed, but the formal 34-35 s benchmark window and vibration frequency were not reached; no benchmark PASS is claimed.","residual_processes":remaining})
    except Exception as e:payload.update({"status":"FAIL","error":f"{type(e).__name__}: {e}","residual_processes":wait_for_process_cleanup(before)})
    write_json(OUT/f"{CASE}.json",payload);print(payload);return 0 if payload["status"]=="PASS" else 1
if __name__=="__main__":
    if "--continue-to" in sys.argv:
        raise SystemExit(continue_existing(float(sys.argv[sys.argv.index("--continue-to")+1])))
    raise SystemExit(postprocess_existing() if "--postprocess-existing" in sys.argv else main())
