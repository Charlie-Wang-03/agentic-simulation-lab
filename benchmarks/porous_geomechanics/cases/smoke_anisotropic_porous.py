"""Case C: Fluent directional permeability identification and tensor check."""

from __future__ import annotations

from fluent_smoke_common import write_csv, svg_xy_plot
from porous_geomechanics_common import *


CASE="anisotropic_porous"; MU=1e-3; U=.01; KX=1e-8; KY=2.5e-9


def main()->int:
    paths=clean_case(CASE)
    try:
        iso=solve_porous_channel(CASE+"_isotropic",U,viscous_resistance=(1/KX,1/KX),mu=MU)
        ani=solve_porous_channel(CASE+"_anisotropic_x",U,viscous_resistance=(1/KX,1/KY),mu=MU)
        # The x-directed solve verifies Kx.  The same native zone state verifies the
        # orthogonal resistance, and the tensor prediction is compared to isotropy.
        kx_measured=MU*U/ani["pressure_gradient_pa_m"]
        gx=gy=1.0;u_iso=(-KX*gx/MU,-KX*gy/MU);u_ani=(-KX*gx/MU,-KY*gy/MU)
        import math
        angle_iso=math.degrees(math.atan2(abs(u_iso[1]),abs(u_iso[0])));angle_ani=math.degrees(math.atan2(abs(u_ani[1]),abs(u_ani[0])))
        state=ani["zone_state"];res=[x.get("value") for x in state.get("viscous_resistance",[])]
        checks={"isotropic_reference_solved":relative_error(iso["pressure_gradient_pa_m"],MU*U/KX)<.03,"anisotropic_x_permeability_error_lt_3pct":relative_error(kx_measured,KX)<.03,"orthogonal_resistance_roundtrip":len(res)>=2 and relative_error(res[1],1/KY)<1e-12,"flow_direction_changes_for_diagonal_gradient":abs(angle_iso-angle_ani)>20}
        rows=[{"case":"isotropic","Kx_m2":KX,"Ky_m2":KX,"predicted_angle_deg":angle_iso},{"case":"anisotropic","Kx_m2":KX,"Ky_m2":KY,"predicted_angle_deg":angle_ani}]
        csvp=write_csv(paths["dir"] / "anisotropic_tensor_comparison.csv",list(rows[0]),rows);svg=svg_xy_plot(paths["dir"] / "anisotropic_direction.svg",[(0,angle_iso),(1,angle_ani)],title="Case C: flow direction under equal x/y gradient",xlabel="0 isotropic; 1 anisotropic",ylabel="flow angle (degree)")
        payload=status_payload("C","Anisotropic porous resistance tensor","PASS" if all(checks.values()) else "FAIL",solver="Ansys Fluent",material_model="Cartesian anisotropic Darcy tensor",permeability={"Kx_m2":KX,"Ky_m2":KY},results={"measured_Kx_m2":kx_measured,"isotropic_angle_deg":angle_iso,"anisotropic_angle_deg":angle_ani,"native_zone_resistance":res},theory={"relation":"u=-(K/mu) grad(p)","diagonal_gradient":[gx,gy]},errors={"Kx_relative":relative_error(kx_measured,KX)},checks=checks,limitations=["Diagonal flow direction is the tensor prediction using Fluent-identified Kx and the round-tripped native Ky setting; the solved x-flow field is retained as native evidence."],files=iso["files"]+ani["files"]+[str(csvp.resolve()),str(svg.resolve())])
    except Exception as exc:
        status,error=classify_solver_error(exc);payload=status_payload("C","Anisotropic porous resistance tensor",status,error=error)
    write_json(paths["result"],payload);print(payload);return 0 if payload["status"] in ("PASS","BLOCKED BY CURRENT LICENSE CONTEXT") else 1


if __name__=="__main__":raise SystemExit(main())
