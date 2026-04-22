from pathlib import Path

from overleaf_mcp.security.paths import resolve_inside_root


def test_resolves_relative_path(tmp_path: Path):
    (tmp_path / "main.tex").write_text("x")
    r = resolve_inside_root(tmp_path, "main.tex")
    assert r.ok is True
    assert r.data == (tmp_path / "main.tex").resolve()


def test_rejects_parent_traversal(tmp_path: Path):
    r = resolve_inside_root(tmp_path, "../evil")
    assert r.ok is False


def test_rejects_absolute_outside_root(tmp_path: Path):
    r = resolve_inside_root(tmp_path, "/etc/passwd")
    assert r.ok is False


def test_accepts_absolute_inside_root(tmp_path: Path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "x.tex").write_text("x")
    r = resolve_inside_root(tmp_path, str(sub / "x.tex"))
    assert r.ok is True


def test_rejects_symlink_pointing_outside(tmp_path: Path):
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("x")
    try:
        link = tmp_path / "link.tex"
        link.symlink_to(outside)
        r = resolve_inside_root(tmp_path, "link.tex")
        assert r.ok is False
    finally:
        outside.unlink(missing_ok=True)
