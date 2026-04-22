from pathlib import Path

from overleaf_mcp.tools.check_consistency import check_consistency


def test_flags_heading_case_inconsistency(tmp_path: Path):
    (tmp_path / "a.tex").write_text("\\section{Title Case Is Used}\n")
    (tmp_path / "b.tex").write_text("\\section{sentence case here}\n")
    r = check_consistency(tmp_path)
    assert r.ok is True
    assert any(f["code"] == "CONS_HEADING_CASE" for f in r.data)


def test_flags_ascii_quotes(tmp_path: Path):
    (tmp_path / "a.tex").write_text("``good'' but \"bad\"\n")
    r = check_consistency(tmp_path)
    assert r.ok is True
    assert any(f["code"] == "CONS_ASCII_QUOTES" for f in r.data)


def test_flags_hyphen_range(tmp_path: Path):
    (tmp_path / "a.tex").write_text("pages 10-20\n")
    r = check_consistency(tmp_path)
    assert r.ok is True
    assert any(f["code"] == "CONS_DASH_STYLE" for f in r.data)
