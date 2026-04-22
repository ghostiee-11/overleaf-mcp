import subprocess
from pathlib import Path

from overleaf_mcp.tools.git_sync import overleaf_status, pull_from_overleaf, push_to_overleaf


def _make_fake_remote(tmp_path: Path) -> tuple[Path, Path]:
    remote = tmp_path / "remote.git"
    remote.mkdir()
    # -b main so the bare repo's HEAD points at main. Without this, on systems where
    # init.defaultBranch is master (older git, default Ubuntu), `git clone` of this
    # bare repo checks out HEAD=master which has no commits, leaving working tree empty.
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main"], cwd=remote, check=True)

    seed = tmp_path / "seed"
    seed.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=seed, check=True)
    (seed / "main.tex").write_text("\\documentclass{article}\\begin{document}hi\\end{document}\n")
    subprocess.run(["git", "add", "main.tex"], cwd=seed, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@x", "-c", "user.name=t", "commit", "-q", "-m", "init"],
        cwd=seed, check=True,
    )
    subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=seed, check=True)
    subprocess.run(["git", "push", "-q", "origin", "main"], cwd=seed, check=True)

    local = tmp_path / "local"
    local.mkdir()
    return remote, local


def test_pull_clones_into_empty_root(tmp_path: Path):
    remote, local = _make_fake_remote(tmp_path)
    r = pull_from_overleaf(local, str(remote), "faketok")
    assert r.ok is True
    assert (local / "main.tex").exists()


def test_push_commits_and_pushes(tmp_path: Path):
    remote, local = _make_fake_remote(tmp_path)
    pull_from_overleaf(local, str(remote), "faketok")
    (local / "main.tex").write_text("new content\n")
    r = push_to_overleaf(local, str(remote), "faketok", "update")
    assert r.ok is True


def test_status_clean_after_pull(tmp_path: Path):
    remote, local = _make_fake_remote(tmp_path)
    pull_from_overleaf(local, str(remote), "faketok")
    r = overleaf_status(local)
    assert r.ok is True
    assert r.data["dirty"] is False


def test_status_dirty_after_edit(tmp_path: Path):
    remote, local = _make_fake_remote(tmp_path)
    pull_from_overleaf(local, str(remote), "faketok")
    (local / "main.tex").write_text("edited\n")
    r = overleaf_status(local)
    assert r.ok is True
    assert r.data["dirty"] is True
