from agentic_simulation_lab.cli import main


def test_cli_list_and_doctor(capsys):
    assert main(["list", "--domain", "mechanics", "--role", "benchmark", "--status", "PASS"]) == 0
    output = capsys.readouterr().out
    assert "mechanics" in output
    assert "ROLE" in output
    assert main(["doctor"]) == 0


def test_cli_dry_run(capsys):
    assert main(["run", "cfd", "--case", "fluent-laminar-channel", "--dry-run", "--json"]) == 0
    assert '"dry_run": true' in capsys.readouterr().out


def test_cli_json_and_invalid_input(capsys):
    assert main(["list", "--solver", "fluent", "--role", "dataset", "--json"]) == 0
    assert '"count"' in capsys.readouterr().out
    assert main(["info", "mechanics", "static-cantilever"]) == 0
    assert "Validation basis:" in capsys.readouterr().out
    assert main(["info", "mechanics", "not-a-case"]) == 2
    assert "unknown case" in capsys.readouterr().err
    assert main(["list", "--domain", "not-a-domain"]) == 2
    assert "unknown domain" in capsys.readouterr().err
