from pathlib import Path

from overleaf_mcp.tools.structure import get_project_structure

ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "checks" / "project"


def test_detects_main_sections_bib():
    r = get_project_structure(ROOT)
    assert r.ok is True
    data = r.data
    assert data["main_file"] == "main.tex"
    assert [s["title"] for s in data["sections"]] == ["Intro", "Details"]
    assert data["bib_files"] == ["refs.bib"]
    assert "chapters/intro" in data["inputs"]
