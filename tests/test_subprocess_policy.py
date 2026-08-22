import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "tools" / "check_subprocess_policy.py"
SPEC = importlib.util.spec_from_file_location("check_subprocess_policy_test", MODULE_PATH)
assert SPEC and SPEC.loader
policy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy)


@pytest.mark.parametrize(
    "source",
    [
        "import subprocess\nsubprocess.run(cmd, timeout=10)",
        "import subprocess as sp\nsp.run(cmd, timeout=10)",
        "from subprocess import run\nrun(cmd, timeout=10)",
        "import subprocess\nsubprocess.run(cmd, timeout=10, shell=False)",
        "import subprocess as sp\nprocess = sp.Popen(cmd)\nprocess.wait(timeout=10)",
    ],
)
def test_safe_subprocess_forms_pass(source):
    assert policy.audit_source(source) == []


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("import os\nos.system(cmd)", "os.system is forbidden"),
        ("from os import system\nsystem(cmd)", "os.system is forbidden"),
        ("import os as operating_system\noperating_system.system(cmd)", "os.system is forbidden"),
        ("import subprocess\nsubprocess.run(cmd)", "requires a timeout"),
        ("import subprocess as sp\nsp.run(cmd)", "requires a timeout"),
        ("from subprocess import run\nrun(cmd)", "requires a timeout"),
        (
            "import subprocess\nsubprocess.run(cmd, timeout=10, shell=True)",
            "shell must be statically False",
        ),
        (
            "import subprocess\nsubprocess.run(cmd, timeout=10, shell=flag)",
            "shell must be statically False",
        ),
        (
            "from subprocess import run as execute\nexecute(cmd, timeout=10, **options)",
            "dynamic keyword arguments are forbidden",
        ),
        ("from subprocess import *\nrun(cmd, timeout=10)", "subprocess star import is forbidden"),
    ],
)
def test_unsafe_subprocess_forms_fail_closed(source, message):
    assert any(message in error for error in policy.audit_source(source))
