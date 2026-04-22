import zipfile
from pathlib import Path

from overleaf_mcp.tools.zip_bridge import export_overleaf_zip, import_overleaf_zip


def test_import_extracts_files(tmp_path: Path):
    zip_path = tmp_path / "in.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("main.tex", "\\documentclass{article}\n")
        zf.writestr("refs.bib", "@article{a,title={x}}\n")
    root = tmp_path / "root"
    root.mkdir()
    r = import_overleaf_zip(root, zip_path)
    assert r.ok is True
    assert "documentclass" in (root / "main.tex").read_text()
    assert "@article" in (root / "refs.bib").read_text()


def test_import_rejects_zip_slip(tmp_path: Path):
    zip_path = tmp_path / "evil.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../evil.tex", "bad")
    root = tmp_path / "root"
    root.mkdir()
    r = import_overleaf_zip(root, zip_path)
    assert r.ok is False


def test_import_rejects_absolute_path(tmp_path: Path):
    zip_path = tmp_path / "abs.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("/etc/passwd", "bad")
    root = tmp_path / "root"
    root.mkdir()
    r = import_overleaf_zip(root, zip_path)
    assert r.ok is False


def test_export_creates_zip(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "main.tex").write_text("hi")
    (root / "chapters").mkdir()
    (root / "chapters" / "intro.tex").write_text("intro")
    out = tmp_path / "out.zip"
    r = export_overleaf_zip(root, out)
    assert r.ok is True
    assert out.exists()
    with zipfile.ZipFile(out) as zf:
        names = sorted(zf.namelist())
    assert "main.tex" in names
    assert "chapters/intro.tex" in names


def test_export_excludes_git_build_and_venv(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "main.tex").write_text("hi")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("x")
    (root / ".build").mkdir()
    (root / ".build" / "main.aux").write_text("x")
    (root / ".venv").mkdir()
    (root / ".venv" / "x").write_text("x")
    out = tmp_path / "out.zip"
    r = export_overleaf_zip(root, out)
    assert r.ok is True
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
    assert not any(n.startswith(".git/") for n in names)
    assert not any(n.startswith(".build/") for n in names)
    assert not any(n.startswith(".venv/") for n in names)
