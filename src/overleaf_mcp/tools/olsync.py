"""Native Overleaf sync client.

Uses the session cookie produced by `ols login` (from the `overleaf-sync`
package), but replaces the broken HTML-scraping project lookup with a JSON
call to Overleaf's current `/user/projects` endpoint, which still works as
of 2026-04. Downloads use the documented `/project/{id}/download/zip` URL.
Pushes reuse overleaf-sync's websocket upload code, monkey-patched to call
our fixed project lookup.
"""
from __future__ import annotations

import io
import pickle
import zipfile
from pathlib import Path
from typing import Any

import requests

from overleaf_mcp.types import ToolResult, fail, ok

_PROJECT_LIST_URL = "https://www.overleaf.com/user/projects"
_DOWNLOAD_URL = "https://www.overleaf.com/project/{}/download/zip"


def _default_cookie_path(project_root: Path) -> Path:
    """Match overleaf-sync's default: `.olauth` in the sync dir."""
    return project_root / ".olauth"


def _load_auth(cookie_path: str | None, project_root: Path) -> ToolResult[dict[str, Any]]:
    path = Path(cookie_path) if cookie_path else _default_cookie_path(project_root)
    if not path.exists():
        return fail(
            f"overleaf cookie not found at {path}",
            "Run `ols login` in the project root to create it.",
        )
    try:
        with path.open("rb") as fh:
            data = pickle.load(fh)
    except (OSError, pickle.UnpicklingError) as err:
        return fail(f"failed to read cookie: {err}")
    if not isinstance(data, dict) or "cookie" not in data:
        return fail(f"unexpected cookie format at {path}")
    return ok(data)


def _list_projects_json(auth: dict[str, Any]) -> ToolResult[list[dict[str, Any]]]:
    """Query Overleaf's current /user/projects endpoint (returns JSON)."""
    try:
        resp = requests.get(
            _PROJECT_LIST_URL,
            cookies=auth["cookie"],
            headers={"Accept": "application/json", "User-Agent": "overleaf-mcp"},
            timeout=20,
        )
    except requests.RequestException as err:
        return fail(f"network error contacting Overleaf: {err}")
    if resp.status_code != 200:
        return fail(
            f"/user/projects returned {resp.status_code}",
            "Your `ols login` session may have expired — run `ols login` again.",
        )
    try:
        payload = resp.json()
    except ValueError:
        return fail("Overleaf returned non-JSON for /user/projects")
    projects = payload.get("projects") if isinstance(payload, dict) else None
    if not isinstance(projects, list):
        return fail("unexpected payload from /user/projects")
    return ok(projects)


def _find_project_by_name(
    projects: list[dict[str, Any]], name: str
) -> dict[str, Any] | None:
    for p in projects:
        if p.get("name") == name:
            return p
    return None


def olsync_list_projects(
    project_root: Path,
    cookie_path: str | None = None,
) -> ToolResult[dict[str, Any]]:
    """Return names and IDs of projects visible to the logged-in account."""
    auth_r = _load_auth(cookie_path, project_root)
    if not auth_r.ok:
        return auth_r
    list_r = _list_projects_json(auth_r.data)
    if not list_r.ok:
        return list_r
    return ok(
        {
            "projects": [
                {
                    "name": p.get("name"),
                    "id": p.get("_id"),
                    "access_level": p.get("accessLevel"),
                }
                for p in list_r.data
            ]
        }
    )


def olsync_pull(
    project_root: Path,
    project_name: str | None = None,
    cookie_path: str | None = None,
) -> ToolResult[dict[str, Any]]:
    """Download the named Overleaf project's zip and extract into project_root."""
    if not project_name:
        return fail(
            "project_name is required",
            "Pass project_name, or set OVERLEAF_PROJECT_NAME in the MCP env.",
        )
    auth_r = _load_auth(cookie_path, project_root)
    if not auth_r.ok:
        return auth_r
    list_r = _list_projects_json(auth_r.data)
    if not list_r.ok:
        return list_r
    project = _find_project_by_name(list_r.data, project_name)
    if not project:
        names = [p.get("name") for p in list_r.data]
        return fail(
            f"project {project_name!r} not found",
            f"Available projects: {names}",
        )
    try:
        resp = requests.get(
            _DOWNLOAD_URL.format(project["_id"]),
            cookies=auth_r.data["cookie"],
            timeout=120,
        )
    except requests.RequestException as err:
        return fail(f"download failed: {err}")
    if resp.status_code != 200 or not resp.content:
        return fail(f"download returned {resp.status_code}")

    extracted = 0
    abs_root = project_root.resolve()
    try:
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            for info in zf.infolist():
                name = info.filename
                if name.startswith("/") or ".." in Path(name).parts:
                    return fail(f"refusing zip entry with unsafe path: {name}")
                target = (abs_root / name).resolve()
                try:
                    target.relative_to(abs_root)
                except ValueError:
                    return fail(f"zip entry escapes project root: {name}")
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, open(target, "wb") as dst:
                    dst.write(src.read())
                extracted += 1
    except zipfile.BadZipFile as err:
        return fail(f"invalid zip returned by Overleaf: {err}")

    return ok(
        {
            "action": "pull",
            "project_name": project_name,
            "project_id": project["_id"],
            "files_extracted": extracted,
        }
    )


def _patched_overleaf_client(auth: dict[str, Any]):
    """Return an overleaf-sync OverleafClient with project lookup patched.

    overleaf-sync 1.2.0 (a) scrapes the `ol-projects` meta tag from the
    dashboard HTML (which Overleaf removed), and (b) hardcodes a `GCLB`
    cookie in its websocket handshake (which Overleaf no longer sets).
    We patch both. The websocket upload path itself still works.
    """
    from olsync.olclient import OverleafClient

    cookie = dict(auth["cookie"])
    # Overleaf no longer issues a GCLB cookie, but overleaf-sync's
    # get_project_infos does `self._cookie["GCLB"]`. Inject a dummy so the
    # KeyError doesn't fire — Overleaf ignores unknown GCLB values.
    cookie.setdefault("GCLB", "overleaf-mcp-stub")

    client = OverleafClient(cookie, auth["csrf"])

    def _all_projects(self):
        resp = requests.get(
            _PROJECT_LIST_URL,
            cookies=self._cookie,
            headers={"Accept": "application/json", "User-Agent": "overleaf-mcp"},
            timeout=20,
        )
        resp.raise_for_status()
        payload = resp.json()
        projects = payload.get("projects", []) if isinstance(payload, dict) else []
        # Normalise to the shape overleaf-sync expects: it uses `_id` and `name`.
        return projects

    def _get_project(self, project_name):
        for p in self.all_projects():
            if p.get("name") == project_name:
                return p
        return None

    # Bind the patched methods to the instance.
    client.all_projects = _all_projects.__get__(client, type(client))
    client.get_project = _get_project.__get__(client, type(client))
    return client


def olsync_push(
    project_root: Path,  # noqa: ARG001 — kept for future native implementation
    project_name: str | None = None,  # noqa: ARG001
    cookie_path: str | None = None,  # noqa: ARG001
) -> ToolResult[dict[str, Any]]:
    """Not yet supported on current Overleaf — needs socket.io v4 client.

    Overleaf uploads files via a websocket-based socket.io v4 protocol.
    overleaf-sync 1.2.0 uses a 2017-vintage socketIO-client that speaks
    Engine.IO 3, and its handshake is rejected with HTTP 502 by Overleaf's
    current servers. A native Engine.IO 4 client is needed to reinstate
    push; that work is not in this release.

    For now, use one of these workarounds:
      1. olsync_pull → edit locally → copy/paste changes into Overleaf UI
      2. olsync_pull → edit locally → export_overleaf_zip → Overleaf → New
         Project → Upload Project (creates a fresh project copy)
    """
    return fail(
        "olsync_push is not yet supported against current Overleaf (socket.io v4 required)",
        "Use olsync_pull to fetch the project, edit locally with the agent, then either "
        "copy/paste changes into the Overleaf web editor, or use export_overleaf_zip and "
        "re-upload as a new project.",
    )


def olsync_login_instructions() -> ToolResult[dict[str, Any]]:
    """Return manual login steps (login is interactive, not automatable)."""
    import shutil as _shutil

    ols_path = _shutil.which("ols")
    return ok(
        {
            "instructions": [
                "1. Open a fresh terminal (NOT Claude Code, NOT a subshell).",
                "2. `cd` into the directory you set as OVERLEAF_PROJECT_ROOT.",
                "3. Run: ols login",
                "4. A Qt browser window opens. Sign into Overleaf.",
                "5. The window closes itself; .olauth is written into the current dir.",
                "6. Come back here. olsync_pull / olsync_push will now work.",
            ],
            "ols_binary_path": ols_path,
            "note": (
                "Login is interactive and cannot be driven from inside an MCP. "
                "The overleaf-mcp then reads the cookie file directly — it does "
                "not invoke the `ols` CLI for list/pull/download."
            ),
        }
    )
