from pathlib import Path

import pytest

from overleaf_mcp.tools.format import check_formatting, format_file, format_snippet


def _messy() -> str:
    return (Path(__file__).resolve().parents[1] / "fixtures" / "messy.tex").read_text()


def test_format_snippet_returns_install_hint_when_missing(
    has_latexindent: bool,
) -> None:
    if has_latexindent:
        pytest.skip("latexindent present; cannot test missing-binary path")
    r = format_snippet(_messy())
    assert r.ok is False
    assert "latexindent" in (r.suggestion or "")


def test_format_snippet_formats_messy_input(has_latexindent: bool) -> None:
    if not has_latexindent:
        pytest.skip("latexindent not installed")
    r = format_snippet(_messy())
    assert r.ok is True
    assert len(r.data["formatted"]) > 0


def test_check_formatting_does_not_modify_disk(
    tmp_path: Path, has_latexindent: bool
) -> None:
    if not has_latexindent:
        pytest.skip("latexindent not installed")
    target = tmp_path / "m.tex"
    target.write_text(_messy())
    before = target.read_text()
    r = check_formatting(tmp_path, "m.tex")
    assert r.ok is True
    assert target.read_text() == before


def test_format_file_modifies_disk(
    tmp_path: Path, has_latexindent: bool
) -> None:
    if not has_latexindent:
        pytest.skip("latexindent not installed")
    target = tmp_path / "m.tex"
    target.write_text(_messy())
    r = format_file(tmp_path, "m.tex")
    assert r.ok is True
