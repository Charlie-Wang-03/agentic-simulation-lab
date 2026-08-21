"""Phase-0 runtime inventory for SPH modules, beta features, and couplings."""

from pathlib import Path
import json
import traceback

from free_surface_sph_common import OUTPUT_ROOT


OUT=OUTPUT_ROOT/"phase0"; OUT.mkdir(parents=True,exist_ok=True); RESULT=OUT/"capabilities.json"
payload={"status":"FAIL"}; original_beta=None
try:
    features=app.GetAdditionalFeatures(); original_beta=features.GetBetaFeaturesEnabled()
    payload["beta_features_originally_enabled"]=original_beta
    features.SetBetaFeaturesEnabled(True)
    project=app.CreateProject(); study=project.GetStudy(); project.SaveProject(str(OUT/"capability_probe.rocky"))
    sph=study.GetSphSettings(); physics=study.GetPhysics(); material=study.CreateFluidMaterial("Probe Fluid")
    modules=study.GetModuleCollection(); module_details={}
    for name in modules.GetModuleNames():
        module=modules.GetModule(name)
        properties=[]
        try: module_properties=module.GetModuleProperties()
        except Exception as exc:
            module_details[name]={"enabled":bool(module.IsModuleEnabled()),"properties_error":repr(exc)}
            continue
        for prop in module_properties:
            item={"name":prop.name,"captions":dict(prop.all_captions)}
            try: item["value"]=module.GetModuleProperty(prop)
            except Exception as exc: item["value_error"]=repr(exc)
            try: item["valid_options"]=module.GetValidOptionsForModuleProperty(prop)
            except Exception: pass
            properties.append(item)
        module_details[name]={"enabled":bool(module.IsModuleEnabled()),"properties":properties}
    payload.update({
        "status":"PASS","application_version":app.GetVersion(),
        "sph_solver_models":sph.GetValidSolverModelValues(),
        "sph_viscous_integration":sph.GetValidViscousForceIntegrationValues(),
        "sph_surface_tension":sph.GetValidSurfaceTensionTypeValues(),
        "sph_turbulence":sph.GetValidTurbulenceTypeValues(),
        "sph_thermal_transfer_models":physics.GetValidSphThermalTransferModelValues(),
        "modules":module_details,
        "fluid_material_module_properties":[],
    })
    try:
        payload["fluid_material_module_properties"]=[{"name":p.name,"captions":dict(p.all_captions)} for p in material.GetModuleProperties()]
    except Exception as exc:
        payload["fluid_material_module_properties_error"]=repr(exc)
except Exception:
    payload["error"]=traceback.format_exc()
finally:
    RESULT.write_text(json.dumps(payload,indent=2,default=str),encoding="utf-8")
    try:
        if original_beta is not None: app.GetAdditionalFeatures().SetBetaFeaturesEnabled(original_beta)
    except Exception: pass
    try: app.Exit()
    except Exception: pass
