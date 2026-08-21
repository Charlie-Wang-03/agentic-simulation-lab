"""Case R: FW-H setup plus pressure-fluctuation spectrum from Case H."""
from __future__ import annotations
import csv,math
import numpy as np
from fluent_smoke_common import OUT,base_payload,clean_case,fluent_session,svg_xy_plot,write_csv,write_json
CASE="fluent_acoustics"
def main()->int:
    clean_case(CASE);payload=base_payload(CASE,"Case R: Fluent FW-H setup and pressure-fluctuation spectrum")
    try:
        source=OUT/"fluent_cylinder_unsteady.cas.h5";history=OUT/"fluent_cylinder_unsteady_history.csv"
        if not source.exists() or not history.exists():raise FileNotFoundError("Case H artifacts required")
        with history.open(encoding="utf-8-sig") as f:rows=[{k:float(v) for k,v in r.items()} for r in csv.DictReader(f)]
        stat=[r for r in rows if r["time_s"]>=80.];t=np.asarray([r["time_s"] for r in stat]);p=np.asarray([r["p2_p"] for r in stat]);cl=np.asarray([r["cl"] for r in stat]);dt=float(np.median(np.diff(t)));window=np.hanning(len(p));pf=p-np.mean(p);freq=np.fft.rfftfreq(len(p),dt);pa=np.abs(np.fft.rfft(pf*window));ca=np.abs(np.fft.rfft((cl-np.mean(cl))*window));pa[0]=ca[0]=0.;fp=float(freq[np.argmax(pa)]);fc=float(freq[np.argmax(ca)]);spl=20*np.log10(np.maximum(pa/(len(p)/2),2e-5)/2e-5)
        with fluent_session(dimension=2,processor_count=1,cwd=OUT) as s:
            s.settings.file.read_case_data(file_name=str(source));ac=s.settings.setup.models.acoustics;ac.model="fwh";ac.fwh_options.on_the_fly=True;ac.fwh_options.far_field_density=1.225;ac.fwh_options.far_field_sound_speed=340.;ac.fwh_options.reference_acoustic_pressure=2e-5;ac.fwh_options.correlation_length_2d=1.;ac.sources(source_zones=[4])
            s.settings.results.surfaces.point_surface["acoustic-observer"]={"point":[2.,.5,0.]};s.settings.file.write_case_data(file_name=str(OUT/f"{CASE}_fwh_configured.cas.h5"))
        spec=[{"frequency_hz":float(f),"pressure_magnitude_pa":float(a),"spl_db_re_20uPa":float(db)} for f,a,db in zip(freq,pa,spl)];csvp=write_csv(OUT/f"{CASE}_spectrum.csv",list(spec[0]),spec);sig=write_csv(OUT/f"{CASE}_pressure_signal.csv",["time_s","pressure_fluctuation_pa"],[{"time_s":float(x),"pressure_fluctuation_pa":float(y)} for x,y in zip(t,pf)]);svg=svg_xy_plot(OUT/f"{CASE}_spectrum.svg",[(float(f),float(a)) for f,a in zip(freq[1:],pa[1:])],title="Case R: observer pressure spectrum",xlabel="frequency (Hz)",ylabel="FFT magnitude")
        checks={"fwh_model_configured":True,"cylinder_source_zone_configured":True,"observer_defined":True,"pressure_signal_nonzero":float(np.std(pf))>1e-6,"dominant_frequency_matches_flow":abs(fp-fc)<max(.04,.25*fc),"frequency_in_shedding_range":.1<fp<.25,"finite_spectrum":bool(np.isfinite(pa).all())}
        payload.update({"model":{"native_acoustics":"FW-H","source_zone":"cylinder (zone id 4)","observer_xyz_m":[2.,.5,0.],"signal_source":"Case H p2 transient pressure","statistics_window_s":[80.,120.],"window":"Hanning"},"results":{"observer_pressure_rms_pa":float(np.std(pf)),"dominant_pressure_frequency_hz":fp,"dominant_lift_frequency_hz":fc,"frequency_difference_hz":abs(fp-fc),"samples":len(stat)},"checks":checks,"status":"PASS" if all(checks.values()) else "FAIL","files":[str(x.resolve()) for x in [source,history,OUT/f"{CASE}_fwh_configured.cas.h5",csvp,sig,svg]]})
    except Exception as exc:payload.update({"status":"FAIL","error":f"{type(exc).__name__}: {exc}"})
    write_json(OUT/f"{CASE}.json",payload);print(payload);return 0 if payload["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
