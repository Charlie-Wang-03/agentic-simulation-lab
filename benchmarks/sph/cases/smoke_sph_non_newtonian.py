"""Case F capability verdict; never substitutes a Newtonian or custom solver."""

from pathlib import Path
import json

from free_surface_sph_common import OUTPUT_ROOT


OUT=OUTPUT_ROOT/"case_f_non_newtonian"; OUT.mkdir(parents=True,exist_ok=True)
capability_path=OUTPUT_ROOT/"phase0"/"capabilities.json"
capabilities=json.loads(capability_path.read_text(encoding="utf-8")) if capability_path.is_file() else {}
module_names=list(capabilities.get("modules",{}))
matching=[name for name in module_names if "newton" in name.lower() or "rheolog" in name.lower() or "viscos" in name.lower()]
payload={
    "case":"F","status":"BLOCKED BY CURRENT PRODUCT MODE",
    "reason":"The installed package has no standalone FreeFlow executable/application entry. Rocky 26.1 SPH works, but its runtime module inventory exposes no non-Newtonian/rheology module, including after a real beta-feature enable-and-restart probe. Only the native constant-viscosity RAFluidMaterial API is callable, so a power-law or Herschel-Bulkley run cannot be configured reliably.",
    "standalone_freeflow_installed":False,"rocky_sph_available":True,
    "beta_restart_probed":capabilities.get("beta_features_originally_enabled") is True,
    "available_module_names":module_names,"matching_non_newtonian_modules":matching,
    "sph_viscous_integration_options":capabilities.get("sph_viscous_integration",[]),
    "substitute_solver_used":False,
}
(OUT/"result.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
print(json.dumps(payload,indent=2))
