from pathlib import Path

from overleaf_mcp.tools.explain_log import explain_log

LOGS = Path(__file__).resolve().parents[1] / "fixtures" / "logs"


def test_parses_undefined_control_sequence():
    log = (LOGS / "undefined_cs.log").read_text()
    r = explain_log(log)
    assert r.ok is True
    errors = r.data["errors"]
    assert len(errors) > 0
    first = errors[0]
    assert first["kind"] == "undefined_control_sequence"
    assert first["file"] == "./main.tex"
    assert first["line"] == 5
    assert "typo" in first["suggestion"].lower() or "usepackage" in first["suggestion"].lower()


def test_parses_missing_dollar():
    log = (LOGS / "missing_dollar.log").read_text()
    r = explain_log(log)
    assert r.ok is True
    assert any(e["kind"] == "missing_dollar" for e in r.data["errors"])


def test_parses_file_not_found():
    log = (LOGS / "file_not_found.log").read_text()
    r = explain_log(log)
    assert r.ok is True
    assert any(e["kind"] == "file_not_found" for e in r.data["errors"])


def test_clean_log_has_no_errors():
    log = (LOGS / "clean.log").read_text()
    r = explain_log(log)
    assert r.ok is True
    assert r.data["errors"] == []
