"""Case I evidence-based blocker for automated two-way SPH-structure coupling."""

from pathlib import Path
import json

from free_surface_sph_common import OUTPUT_ROOT


OUT=OUTPUT_ROOT/"case_i_flexible_structure"; OUT.mkdir(parents=True,exist_ok=True)
payload={
    "case":"I","status":"BLOCKED BY CURRENT API",
    "reason":"Rocky 26.1 exposes SystemCouplingWall preprocessing, structural-coupling flags, and FEM-force export, but the only supported host-side participant session is PyRocky. On this installed 26.1/ansys-rocky-core 0.4.1 combination the real RPC handshake succeeds and the server resets on GetVersion/CreateProject (WinError 10054), already reproduced in the Rocky suite. The built-in headless PrePost script runs inside Rocky and cannot simultaneously supply the participant_session required by PySystemCoupling. Therefore a synchronized two-way SPH<->Mechanical solve cannot be orchestrated reliably; no one-way or home-grown plate model is substituted.",
    "installed_system_coupling_module":"C:\\Program Files\\ANSYS Inc\\ANSYS Student\\v261\\rocky\\Modules\\26.1.0\\system_coupling_module",
    "prepost_capabilities":["ImportSystemCouplingWall","EnableStructuralCouplingType","EnableFEMForces","ExportFEMForces"],
    "pyrocky_version":"0.4.1","rocky_version":"26.1.0","rpc_error":"ConnectionResetError: [WinError 10054] An existing connection was forcibly closed by the remote host",
    "substitute_fsi_used":False,
}
(OUT/"result.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
print(json.dumps(payload,indent=2))
