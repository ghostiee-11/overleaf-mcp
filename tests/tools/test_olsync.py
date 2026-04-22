"""Tests for the native olsync client (patched project lookup + downloads)."""
import io
import pickle
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from overleaf_mcp.tools import olsync


@pytest.fixture
def fake_cookie(tmp_path: Path) -> Path:
    """Write a pickle at tmp_path/.olauth that looks like overleaf-sync's format."""
    (tmp_path / ".olauth").write_bytes(
        pickle.dumps({"cookie": {"overleaf_session2": "abc"}, "csrf": "xyz"})
    )
    return tmp_path / ".olauth"


class _FakeResp:
    def __init__(self, status=200, payload=None, content=b""):
        self.status_code = status
        self._payload = payload
        self.content = content

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")


def test_list_projects_parses_user_projects_endpoint(tmp_path, fake_cookie):
    payload = {
        "projects": [
            {"_id": "abc", "name": "Paper", "accessLevel": "owner"},
            {"_id": "def", "name": "Thesis 2026", "accessLevel": "readAndWrite"},
        ]
    }

    def fake_get(url, **kwargs):
        assert url.endswith("/user/projects")
        return _FakeResp(200, payload)

    with patch("overleaf_mcp.tools.olsync.requests.get", side_effect=fake_get):
        r = olsync.olsync_list_projects(tmp_path)
    assert r.ok is True
    names = [p["name"] for p in r.data["projects"]]
    assert names == ["Paper", "Thesis 2026"]
    assert r.data["projects"][0]["id"] == "abc"


def test_list_reports_missing_cookie(tmp_path):
    r = olsync.olsync_list_projects(tmp_path)
    assert r.ok is False
    assert "cookie not found" in r.error
    assert "ols login" in (r.suggestion or "")


def test_pull_requires_project_name(tmp_path, fake_cookie):
    r = olsync.olsync_pull(tmp_path)
    assert r.ok is False
    assert "project_name is required" in r.error


def test_pull_extracts_downloaded_zip(tmp_path, fake_cookie):
    # Build a fake zip containing main.tex + chapters/intro.tex
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("main.tex", b"\\documentclass{article}\n")
        zf.writestr("chapters/intro.tex", b"Hello.\n")
    zip_bytes = buf.getvalue()

    projects_payload = {
        "projects": [{"_id": "ID123", "name": "MyProject", "accessLevel": "owner"}]
    }

    def fake_get(url, **kwargs):
        if url.endswith("/user/projects"):
            return _FakeResp(200, projects_payload)
        if "/download/zip" in url:
            assert "ID123" in url
            return _FakeResp(200, content=zip_bytes)
        raise AssertionError(f"unexpected URL {url}")

    with patch("overleaf_mcp.tools.olsync.requests.get", side_effect=fake_get):
        r = olsync.olsync_pull(tmp_path, project_name="MyProject")

    assert r.ok is True
    assert r.data["files_extracted"] == 2
    assert (tmp_path / "main.tex").read_text() == "\\documentclass{article}\n"
    assert (tmp_path / "chapters" / "intro.tex").read_text() == "Hello.\n"


def test_pull_rejects_zip_slip(tmp_path, fake_cookie):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../escape.tex", b"bad")
    zip_bytes = buf.getvalue()

    projects_payload = {
        "projects": [{"_id": "ID1", "name": "P", "accessLevel": "owner"}]
    }

    def fake_get(url, **kwargs):
        if url.endswith("/user/projects"):
            return _FakeResp(200, projects_payload)
        return _FakeResp(200, content=zip_bytes)

    with patch("overleaf_mcp.tools.olsync.requests.get", side_effect=fake_get):
        r = olsync.olsync_pull(tmp_path, project_name="P")
    assert r.ok is False
    assert "unsafe" in r.error or "escape" in r.error


def test_pull_reports_unknown_project_with_available_list(tmp_path, fake_cookie):
    payload = {"projects": [{"_id": "a", "name": "Paper", "accessLevel": "owner"}]}

    def fake_get(url, **kwargs):
        return _FakeResp(200, payload)

    with patch("overleaf_mcp.tools.olsync.requests.get", side_effect=fake_get):
        r = olsync.olsync_pull(tmp_path, project_name="Missing")
    assert r.ok is False
    assert "not found" in r.error
    assert "Paper" in (r.suggestion or "")


def test_list_reports_auth_failure_with_hint(tmp_path, fake_cookie):
    def fake_get(url, **kwargs):
        return _FakeResp(302)

    with patch("overleaf_mcp.tools.olsync.requests.get", side_effect=fake_get):
        r = olsync.olsync_list_projects(tmp_path)
    assert r.ok is False
    assert "ols login" in (r.suggestion or "")


def test_login_instructions_always_available(tmp_path):
    r = olsync.olsync_login_instructions()
    assert r.ok is True
    assert "ols login" in " ".join(r.data["instructions"])


def test_push_requires_project_name(tmp_path, fake_cookie):
    r = olsync.olsync_push(tmp_path)
    assert r.ok is False
    assert "project_name is required" in r.error


def test_push_reports_missing_cookie(tmp_path):
    r = olsync.olsync_push(tmp_path, project_name="X")
    assert r.ok is False
    assert "cookie not found" in r.error


def test_push_uploads_each_top_level_file(tmp_path, fake_cookie, monkeypatch):
    """End-to-end internal test with HTTP + websocket mocked at boundary."""
    (tmp_path / "main.tex").write_bytes(b"\\documentclass{article}\n")
    (tmp_path / "refs.bib").write_bytes(b"@article{x,title={y}}\n")
    (tmp_path / ".DS_Store").write_bytes(b"ignore me")
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "intro.tex").write_bytes(b"nested\n")

    projects_payload = {
        "projects": [{"_id": "P1", "name": "MyProj", "accessLevel": "owner"}]
    }
    upload_calls: list[dict] = []
    import overleaf_mcp.tools.olsync as mod

    # Patch the module-level requests.get for _list_projects_json
    monkeypatch.setattr(
        mod.requests,
        "get",
        lambda *a, **k: _FakeResp(200, projects_payload),
    )
    # Patch the internal helpers directly — simpler than faking Session
    monkeypatch.setattr(
        mod,
        "_fetch_fresh_csrf",
        lambda _session, _pid: olsync.ok("FRESH_CSRF"),
    )
    monkeypatch.setattr(
        mod,
        "_fetch_project_tree",
        lambda _session, _pid: olsync.ok({"rootFolder": [{"_id": "ROOT"}]}),
    )

    def fake_upload(session, project_id, csrf, folder_id, remote_name, content):
        upload_calls.append({
            "project_id": project_id,
            "csrf": csrf,
            "folder_id": folder_id,
            "remote_name": remote_name,
            "content": content,
        })
        return True, f"ent_{remote_name}"

    monkeypatch.setattr(mod, "_upload_single_file", fake_upload)

    r = olsync.olsync_push(tmp_path, project_name="MyProj")
    assert r.ok is True, r.error
    assert r.data["files_uploaded"] == 2  # main.tex + refs.bib
    assert "chapters/" in r.data["skipped_nested_dirs"]
    names = {c["remote_name"] for c in upload_calls}
    assert names == {"main.tex", "refs.bib"}
    for c in upload_calls:
        assert c["folder_id"] == "ROOT"
        assert c["csrf"] == "FRESH_CSRF"
        assert c["project_id"] == "P1"
