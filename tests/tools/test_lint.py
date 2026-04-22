from pathlib import Path

import pytest

from overleaf_mcp.tools.lint import lint_file


def _warnings_source() -> str:
    return (Path(__file__).resolve().parents[1] / "fixtures" / "warnings.tex").read_text()


def test_returns_install_hint_when_chktex_missing(
    tmp_path: Path, has_chktex: bool
) -> None:
    if has_chktex:
        pytest.skip("chktex present")
    (tmp_path / "w.tex").write_text("hi")
    r = lint_file(tmp_path, "w.tex")
    assert r.ok is False
    assert "chktex" in (r.suggestion or "")


def test_parses_warnings(tmp_path: Path, has_chktex: bool) -> None:
    if not has_chktex:
        pytest.skip("chktex not installed")
    (tmp_path / "w.tex").write_text(_warnings_source())
    r = lint_file(tmp_path, "w.tex")
    assert r.ok is True
    assert len(r.data["warnings"]) > 0
    w = r.data["warnings"][0]
    assert isinstance(w["line"], int)
    assert isinstance(w["column"], int)
    assert isinstance(w["message"], str)
