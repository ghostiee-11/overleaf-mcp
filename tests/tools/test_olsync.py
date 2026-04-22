"""Tests for the overleaf-sync wrapper tools.

Uses mocked subprocess — we never call the real ols binary to avoid network and
to run in CI without credentials.
"""
from pathlib import Path
from unittest.mock import patch

import pytest

from overleaf_mcp import capability
from overleaf_mcp.tools import olsync


class _FakeResult:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@pytest.fixture(autouse=True)
def _mock_ols_available(monkeypatch):
    """Pretend `ols` is installed regardless of host machine."""
    capability.reset_capability_cache()
    cap_dict = {
        "latexindent": capability.Capability(available=False, suggestion="x"),
        "chktex": capability.Capability(available=False, suggestion="x"),
        "latexmk": capability.Capability(available=False, suggestion="x"),
        "ols": capability.Capability(available=True, version="ols, version 1.2.0"),
    }
    monkeypatch.setattr(capability, "_cache", cap_dict)
    yield
    capability.reset_capability_cache()


def test_pull_calls_ols_with_remote_only(tmp_path: Path):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return _FakeResult(returncode=0, stdout="Remote files synced.\n")

    with patch("overleaf_mcp.tools.olsync.subprocess.run", side_effect=fake_run):
        r = olsync.olsync_pull(tmp_path, project_name="My Project")
    assert r.ok is True
    assert r.data["action"] == "pull"
    # Exactly one ols invocation, with -r / --remote-only, -n, -p
    assert len(calls) == 1
    argv = calls[0]
    assert argv[0] == "ols"
    assert "--remote-only" in argv
    assert "-n" in argv and "My Project" in argv
    assert "-p" in argv and str(tmp_path) in argv


def test_push_calls_ols_with_local_only(tmp_path: Path):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return _FakeResult(returncode=0, stdout="Pushed.\n")

    with patch("overleaf_mcp.tools.olsync.subprocess.run", side_effect=fake_run):
        r = olsync.olsync_push(tmp_path, project_name="MyProj", cookie_path="/tmp/olauth")
    assert r.ok is True
    assert r.data["action"] == "push"
    argv = calls[0]
    assert "--local-only" in argv
    assert "--store-path" in argv and "/tmp/olauth" in argv


def test_pull_reports_failure_with_suggestion(tmp_path: Path):
    def fake_run(args, **kwargs):
        return _FakeResult(returncode=1, stderr="Login expired\n")

    with patch("overleaf_mcp.tools.olsync.subprocess.run", side_effect=fake_run):
        r = olsync.olsync_pull(tmp_path, project_name="P")
    assert r.ok is False
    assert "Login expired" in r.error
    assert "ols login" in (r.suggestion or "")


def test_list_projects_parses_stdout_lines():
    def fake_run(args, **kwargs):
        return _FakeResult(returncode=0, stdout="My Paper\nThesis 2026\n")

    with patch("overleaf_mcp.tools.olsync.subprocess.run", side_effect=fake_run):
        r = olsync.olsync_list_projects()
    assert r.ok is True
    assert r.data["projects"] == ["My Paper", "Thesis 2026"]


def test_returns_install_hint_when_ols_missing(tmp_path: Path, monkeypatch):
    cap_dict = {
        "latexindent": capability.Capability(available=False, suggestion="x"),
        "chktex": capability.Capability(available=False, suggestion="x"),
        "latexmk": capability.Capability(available=False, suggestion="x"),
        "ols": capability.Capability(
            available=False, suggestion="install overleaf-sync"
        ),
    }
    monkeypatch.setattr(capability, "_cache", cap_dict)
    r = olsync.olsync_pull(tmp_path, project_name="x")
    assert r.ok is False
    assert "ols" in r.error.lower() or "overleaf-sync" in r.error.lower()
    assert r.suggestion == "install overleaf-sync"


def test_login_instructions_returned_even_without_ols():
    # Login instructions are informational — should work regardless.
    r = olsync.olsync_login_instructions()
    assert r.ok is True
    assert "ols login" in " ".join(r.data["instructions"])
