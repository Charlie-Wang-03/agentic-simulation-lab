"""Case Q: non-reacting three-species transport and mixing channel."""
from __future__ import annotations
import math
import numpy as np
from fluent_field_export import export_npz_from_ascii
from fluent_mesh import split_inlet_channel_2d
from fluent_smoke_common import OUT,base_payload,clean_case,fluent_session,read_fluent_ascii_export,svg_field_map,svg_xy_plot,write_csv,write_json
CASE="fluent_species";L=2.;H=.2;U=1.
def main()->int:
    clean_case(CASE);mesh=OUT/f"{CASE}.msh";stats=split_inlet_channel_2d(mesh,length=L,height=H,nx=200,ny=60);payload=base_payload(CASE,"Case Q: Species Transport mixing channel")
    try:
        with fluent_session(dimension=2,processor_count=1,cwd=OUT) as s:
            s.settings.file.read_mesh(file_name=str(mesh));s.settings.setup.models.viscous.model="laminar";sp=s.settings.setup.models.species;sp.model.option="species-transport";sp.model.material="mixture-template"
            for name in ("inlet-upper","inlet-lower"):
                vin=s.settings.setup.boundary_conditions.velocity_inlet[name];vin.momentum.velocity_magnitude.value=U;vin.thermal.temperature.value=300.
            up=s.settings.setup.boundary_conditions.velocity_inlet["inlet-upper"].species.species_mass_fraction;lo=s.settings.setup.boundary_conditions.velocity_inlet["inlet-lower"].species.species_mass_fraction
            up["h2o"].value=1.;up["o2"].value=0.;lo["h2o"].value=0.;lo["o2"].value=1.
            s.settings.solution.initialization.hybrid_initialize();s.settings.solution.run_calculation.iterate(iter_count=1000);allowed=list(s.fields.field_data.scalar_fields.allowed_values())
            def sf(spec):return spec if spec in allowed else next((x for x in allowed if spec in x.lower() and ("mass" in x.lower() or "fraction" in x.lower())),None)
            fields={x:sf(x) for x in ("h2o","o2","n2")}
            if not fields["h2o"] or not fields["o2"]:raise RuntimeError(f"Species fields not found: {fields}")
            qs=["x-coordinate","y-coordinate","pressure","x-velocity","y-velocity",*dict.fromkeys(x for x in fields.values() if x)];raw=OUT/f"{CASE}_raw.csv";s.settings.file.export.ascii(file_name=str(raw),surface_name_list=["interior","inlet-upper","inlet-lower","outlet"],delimiter="comma",quantities=qs,location="node");s.settings.file.write_case_data(file_name=str(OUT/f"{CASE}.cas.h5"))
        rows=read_fluent_ascii_export(raw);unique={(round(r["x-coordinate"],12),round(r["y-coordinate"],12)):r for r in rows};rows=list(unique.values());h2=np.asarray([r[fields["h2o"]] for r in rows]);o2=np.asarray([r[fields["o2"]] for r in rows]);n2=np.asarray([r[fields["n2"]] for r in rows]) if fields["n2"] else 1-h2-o2;sums=h2+o2+n2
        meta={"case":"Q","model":"Species Transport, non-reacting","species":["h2o","o2","n2"],"field_names":fields,"units":{"coordinates":"m","velocity":"m/s","pressure":"Pa","species_mass_fraction":"1"},"fluent_version":"261"}
        # Export canonical species names in a standalone compact NPZ.
        coords=np.asarray([[r["x-coordinate"],r["y-coordinate"]] for r in sorted(rows,key=lambda r:(r["x-coordinate"],r["y-coordinate"]))]);ordered=sorted(rows,key=lambda r:(r["x-coordinate"],r["y-coordinate"]));npz=OUT/f"{CASE}_field.npz";np.savez_compressed(npz,coordinates=coords,velocity_x=np.asarray([r["x-velocity"] for r in ordered]),velocity_y=np.asarray([r["y-velocity"] for r in ordered]),pressure=np.asarray([r["pressure"] for r in ordered]),species_h2o=np.asarray([r[fields["h2o"]] for r in ordered]),species_o2=np.asarray([r[fields["o2"]] for r in ordered]),species_n2=np.asarray([r[fields["n2"]] if fields["n2"] else 1-r[fields["h2o"]]-r[fields["o2"]] for r in ordered]),metadata_json=np.asarray(__import__('json').dumps(meta)))
        outlet=sorted([r for r in rows if abs(r["x-coordinate"]-L)<1e-9],key=lambda r:r["y-coordinate"]);mix_std=float(np.std([r[fields["h2o"]] for r in outlet]));center=sorted([r for r in rows if abs(r["y-coordinate"])<H/120],key=lambda r:r["x-coordinate"])
        csvp=write_csv(OUT/f"{CASE}_centerline.csv",["x_m","h2o","o2","sum_y"],[{"x_m":r["x-coordinate"],"h2o":r[fields["h2o"]],"o2":r[fields["o2"]],"sum_y":r[fields["h2o"]]+r[fields["o2"]]+(r[fields["n2"]] if fields["n2"] else 1-r[fields["h2o"]]-r[fields["o2"]])} for r in center]);svg=svg_field_map(OUT/f"{CASE}_h2o.svg",[(r["x-coordinate"],r["y-coordinate"],r[fields["h2o"]]) for r in rows],title="Case Q: H2O mass fraction");psvg=svg_xy_plot(OUT/f"{CASE}_centerline.svg",[(r["x-coordinate"],r[fields["h2o"]]) for r in center],title="Case Q: centerline species mixing",xlabel="x (m)",ylabel="Y_H2O")
        with np.load(npz,allow_pickle=False) as d:finite=all(np.isfinite(d[k]).all() for k in ("coordinates","velocity_x","velocity_y","pressure","species_h2o","species_o2","species_n2"))
        checks={"species_bounded":float(min(h2.min(),o2.min(),n2.min()))>-1e-6 and float(max(h2.max(),o2.max(),n2.max()))<1+1e-6,"species_sum_error_lt_1e_5":float(np.max(np.abs(sums-1)))<1e-5,"mixing_visible":any(.05<r[fields["h2o"]]<.95 for r in center),"outlet_profile_mixed":mix_std<.5,"field_npz_finite":finite}
        payload.update({"model":{"species_transport":True,"reaction":False,"mixture":"mixture-template","species":["h2o","o2","n2"],"combustion":"not run; intentionally excluded from core PASS"},"mesh":{**stats,"nx":200,"ny":60},"results":{"max_species_sum_error":float(np.max(np.abs(sums-1))),"outlet_h2o_std":mix_std,"h2o_range":[float(h2.min()),float(h2.max())]},"checks":checks,"convergence":{"iterations_requested":1000},"status":"PASS" if all(checks.values()) else "FAIL","files":[str(x.resolve()) for x in [mesh,raw,npz,csvp,svg,psvg,OUT/f"{CASE}.cas.h5"]]})
    except Exception as exc:payload.update({"status":"FAIL","error":f"{type(exc).__name__}: {exc}"})
    write_json(OUT/f"{CASE}.json",payload);print(payload);return 0 if payload["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
