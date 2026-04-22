from pathlib import Path

from overleaf_mcp.config import load_config


def test_requires_project_root():
    r = load_config({})
    assert r.ok is False


def test_project_root_must_exist(tmp_path: Path):
    r = load_config({"OVERLEAF_PROJECT_ROOT": str(tmp_path / "nope")})
    assert r.ok is False


def test_local_mode(tmp_path: Path):
    r = load_config({"OVERLEAF_PROJECT_ROOT": str(tmp_path)})
    assert r.ok is True
    assert r.data.mode == "local"
    assert r.data.project_root == tmp_path.resolve()
    assert r.data.git_url is None
    assert r.data.git_token is None


def test_synced_mode(tmp_path: Path):
    r = load_config({
        "OVERLEAF_PROJECT_ROOT": str(tmp_path),
        "OVERLEAF_GIT_URL": "https://git.overleaf.com/abc",
        "OVERLEAF_GIT_TOKEN": "tok",
    })
    assert r.ok is True
    assert r.data.mode == "synced"
    assert r.data.git_url == "https://git.overleaf.com/abc"
    assert r.data.git_token == "tok"


def test_partial_sync_env_falls_back_to_local(tmp_path: Path):
    r = load_config({
        "OVERLEAF_PROJECT_ROOT": str(tmp_path),
        "OVERLEAF_GIT_URL": "https://x",
        # no token
    })
    assert r.ok is True
    assert r.data.mode == "local"
