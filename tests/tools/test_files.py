from pathlib import Path

from overleaf_mcp.tools.files import list_tex_files, read_tex_file, write_tex_file


def _mk_project(root: Path) -> None:
    (root / "main.tex").write_text("\\documentclass{article}\n")
    (root / "refs.bib").write_text("@article{foo,title={F}}\n")
    (root / "chapters").mkdir()
    (root / "chapters" / "intro.tex").write_text("Intro.\n")
    (root / "README.md").write_text("not latex")


def test_lists_tex_files_recursively(tmp_path: Path):
    _mk_project(tmp_path)
    r = list_tex_files(tmp_path)
    assert r.ok is True
    assert sorted(r.data) == ["chapters/intro.tex", "main.tex", "refs.bib"]


def test_reads_file_with_line_count(tmp_path: Path):
    _mk_project(tmp_path)
    r = read_tex_file(tmp_path, "main.tex")
    assert r.ok is True
    assert "\\documentclass{article}" in r.data["content"]
    assert r.data["lines"] == 1  # one complete line terminated by newline


def test_rejects_read_outside_root(tmp_path: Path):
    _mk_project(tmp_path)
    r = read_tex_file(tmp_path, "../escape.tex")
    assert r.ok is False


def test_write_is_atomic_and_round_trips(tmp_path: Path):
    _mk_project(tmp_path)
    body = "\\documentclass{article}\n\\begin{document}hi\\end{document}\n"
    w = write_tex_file(tmp_path, "new.tex", body)
    assert w.ok is True
    assert w.data["bytes"] == len(body.encode("utf-8"))
    r = read_tex_file(tmp_path, "new.tex")
    assert r.ok is True
    assert r.data["content"] == body


def test_write_creates_missing_parent_dirs(tmp_path: Path):
    _mk_project(tmp_path)
    w = write_tex_file(tmp_path, "new/dir/file.tex", "x")
    assert w.ok is True
    assert (tmp_path / "new" / "dir" / "file.tex").read_text() == "x"
