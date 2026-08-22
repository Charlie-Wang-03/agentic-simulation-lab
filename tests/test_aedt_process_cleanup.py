import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

MODULE_PATH = (
    Path(__file__).parents[1]
    / "benchmarks"
    / "electromagnetics"
    / "common"
    / "aedt_smoke_common.py"
)
SPEC = importlib.util.spec_from_file_location("aedt_smoke_common_cleanup_test", MODULE_PATH)
assert SPEC and SPEC.loader
aedt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(aedt)


class _NoSuchProcess(Exception):
    pass


class _AccessDenied(Exception):
    pass


class _FakeProcess:
    def __init__(self, pid, children, events):
        self.pid = pid
        self._children = children
        self._events = events
        self.alive = True

    def children(self, *, recursive):
        assert recursive is True
        return list(self._children)

    def terminate(self):
        self._events.append(("terminate", self.pid))
        self.alive = False

    def kill(self):
        self._events.append(("kill", self.pid))
        self.alive = False


class _UnreadableChildrenProcess(_FakeProcess):
    def children(self, *, recursive):
        assert recursive is True
        raise _AccessDenied(self.pid)


def _fake_psutil(processes, factory_calls):
    def process(pid):
        factory_calls.append(pid)
        if pid not in processes:
            raise _NoSuchProcess(pid)
        return processes[pid]

    def wait_procs(candidates, timeout):
        assert timeout in {5, 10}
        alive = [candidate for candidate in candidates if candidate.alive]
        return [candidate for candidate in candidates if not candidate.alive], alive

    return SimpleNamespace(
        Process=process,
        NoSuchProcess=_NoSuchProcess,
        AccessDenied=_AccessDenied,
        wait_procs=wait_procs,
    )


def test_cleanup_terminates_only_explicit_owned_pid_and_confirmed_descendants(monkeypatch):
    events = []
    calls = []
    child = _FakeProcess(101, [], events)
    grandchild = _FakeProcess(102, [], events)
    parent = _FakeProcess(100, [child, grandchild], events)
    unrelated = _FakeProcess(200, [], events)
    processes = {100: parent, 101: child, 102: grandchild, 200: unrelated}
    monkeypatch.setitem(sys.modules, "psutil", _fake_psutil(processes, calls))

    result = aedt.cleanup_owned_process(100)

    assert result["status"] == "CLEANED"
    assert result["ownership"] == "API_AEDT_PROCESS_ID"
    assert result["confirmed_descendants"] == [101, 102]
    assert calls == [100]
    assert events == [("terminate", 101), ("terminate", 102), ("terminate", 100)]
    assert unrelated.alive is True


def test_constructor_failure_without_owned_pid_is_non_destructive(monkeypatch):
    calls = []
    monkeypatch.setitem(sys.modules, "psutil", _fake_psutil({}, calls))

    result = aedt.cleanup_owned_process(None)

    assert result == {
        "pid": None,
        "ownership": "NOT_CONFIRMED",
        "status": "NOT_CONFIRMED",
        "attempted": False,
        "forced": False,
        "remaining": [],
        "reason": "No process identifier was returned by the current AEDT session constructor.",
    }
    assert calls == []


def test_unconfirmed_descendants_block_all_destructive_cleanup(monkeypatch):
    events = []
    calls = []
    parent = _UnreadableChildrenProcess(100, [], events)
    monkeypatch.setitem(sys.modules, "psutil", _fake_psutil({100: parent}, calls))

    result = aedt.cleanup_owned_process(100)

    assert result["status"] == "BLOCKED"
    assert result["attempted"] is False
    assert events == []


def test_aedt_cases_do_not_infer_process_ownership_from_pid_differences():
    cases = MODULE_PATH.parents[1] / "cases"
    sources = "\n".join(path.read_text(encoding="utf-8") for path in cases.glob("*.py"))
    assert "cleanup_new_aedt_processes" not in sources
    assert "aedt_pid_set" not in sources
