from ansys.mechanical.core import launch_mechanical

EXEC_FILE = (
    r"C:\Program Files\ANSYS Inc\ANSYS Student\v261"
    r"\aisol\bin\winx64\AnsysWBU.exe"
)
AWP_ROOT261 = r"C:\Program Files\ANSYS Inc\ANSYS Student\v261"

print("=== Launching Mechanical ===")

mechanical = None

try:
    mechanical = launch_mechanical(
        exec_file=EXEC_FILE,
        batch=True,
        start_instance=True,
        cleanup_on_exit=True,
        loglevel="INFO",
        additional_envs={"AWP_ROOT261": AWP_ROOT261},
        verbose_mechanical=True,
    )

    print("=== Connected ===")
    print(mechanical)

    version = str(mechanical.version)
    print("Version:", version)
    print("Alive:", mechanical.is_alive)
    assert version == "261", f"Expected Mechanical 261, got {version!r}"

    result = mechanical.run_python_script("2 + 3")
    print("2 + 3 =", result)
    assert str(result) == "5", f"Expected 5, got {result!r}"

    product_version = mechanical.run_python_script(
        "ExtAPI.DataModel.Project.ProductVersion"
    )
    print("Mechanical product version:", product_version)

    analysis_result = mechanical.run_python_script(
        """
analysis = Model.AddStaticStructuralAnalysis()
analysis.Name
"""
    )
    print("Created analysis:", analysis_result)
    assert analysis_result, "Static Structural analysis creation returned no name"

    print("=== SMOKE TEST PASSED ===")
finally:
    if mechanical is not None:
        print("=== Closing Mechanical normally ===")
        mechanical.exit(force=False)
        print("Alive after exit:", mechanical.is_alive)
