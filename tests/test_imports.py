import subprocess
import sys


def test_import_does_not_load_solver_packages():
    code = "import sys, agentic_simulation_lab; print(any(x.startswith('ansys.') for x in sys.modules))"
    completed = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True, timeout=30
    )
    assert completed.stdout.strip() == "False"


def test_dataset_metadata_module_does_not_import_numpy_or_solver_packages():
    code = (
        "import sys, agentic_simulation_lab.datasets; "
        "print('numpy' in sys.modules, any(x.startswith('ansys.') for x in sys.modules))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True, timeout=30
    )
    assert completed.stdout.strip() == "False False"
