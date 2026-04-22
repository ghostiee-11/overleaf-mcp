from pathlib import Path

import pytest

from overleaf_mcp.tools.compile import compile_file


def test_returns_install_hint_when_latexmk_missing(
    tmp_path: Path, has_latexmk: bool
) -> None:
    if has_latexmk:
        pytest.skip("latexmk present")
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\\begin{document}hi\\end{document}\n"
    )
    r = compile_file(tmp_path, "main.tex")
    assert r.ok is False
    assert "latexmk" in (r.suggestion or "").lower() or "tex live" in (r.suggestion or "").lower()


def test_compiles_trivial_document(tmp_path: Path, has_latexmk: bool) -> None:
    if not has_latexmk:
        pytest.skip("latexmk not installed")
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\\begin{document}hello\\end{document}\n"
    )
    r = compile_file(tmp_path, "main.tex")
    assert r.ok is True
    assert r.data["success"] is True
    assert r.data["pdf_path"].endswith(".pdf")
    assert (tmp_path / r.data["pdf_path"]).exists()


def test_returns_parsed_errors_for_broken_document(
    tmp_path: Path, has_latexmk: bool
) -> None:
    if not has_latexmk:
        pytest.skip("latexmk not installed")
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\\begin{document}\\undefinedthing\\end{document}\n"
    )
    r = compile_file(tmp_path, "main.tex")
    assert r.ok is True
    assert r.data["success"] is False
    assert len(r.data["errors"]) > 0
    assert any(e["kind"] == "undefined_control_sequence" for e in r.data["errors"])
