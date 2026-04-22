"""Native Overleaf sync client.

Uses the session cookie produced by `ols login` (from the `overleaf-sync`
package), but talks to Overleaf directly via HTTP:

- List:   GET /user/projects (JSON)
- Pull:   GET /project/{id}/download/zip → unzip into project_root
- Push:   POST /project/{id}/upload?folder_id=...  with multipart body
          {name=<filename>, relativePath=null, qqfile=<bytes>} — overwrites
          a doc of the same name in place.

This replaces the broken overleaf-sync 1.2.0 paths: it scraped an `ol-projects`
meta tag Overleaf removed, and its socket.io upload used a 2017-era client
that Overleaf rejects.
"""
from __future__ import annotations

import io
import pickle
import re
import zipfile
from pathlib import Path
from typing import Any

import requests

from overleaf_mcp.types import ToolResult, fail, ok

_PROJECT_LIST_URL = "https://www.overleaf.com/user/projects"
_DOWNLOAD_URL = "https://www.overleaf.com/project/{}/download/zip"
_UPLOAD_URL = "https://www.overleaf.com/project/{}/upload"
_EDITOR_URL = "https://www.overleaf.com/project/{}"
_CSRF_RE = re.compile(r'<meta name="ol-csrfToken" content="([^"]+)"')
_USER_AGENT = "Mozilla/5.0 overleaf-mcp"

# Files and dirs we never push to Overleaf
_PUSH_EXCLUDE_DIRS: set[str] = {
    ".git", ".build", ".venv", "node_modules", "__pycache__",
}
_PUSH_EXCLUDE_FILES: set[str] = {".olauth", ".DS_Store"}


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


def _fetch_fresh_csrf(
    session: requests.Session, project_id: str
) -> ToolResult[str]:
    """Load the editor page to pick up a fresh CSRF token."""
    try:
        resp = session.get(_EDITOR_URL.format(project_id), timeout=20)
    except requests.RequestException as err:
        return fail(f"could not reach editor page: {err}")
    if resp.status_code != 200:
        return fail(
            f"editor page returned {resp.status_code} — session may be invalid",
            "Your `ols login` session may have expired; run `ols login` again.",
        )
    m = _CSRF_RE.search(resp.text)
    if not m:
        return fail("could not extract CSRF token from editor page")
    return ok(m.group(1))


def _fetch_project_tree(
    session: requests.Session, project_id: str
) -> ToolResult[dict[str, Any]]:
    """Fetch the project's full folder tree via the socket.io v0.9 websocket.

    Overleaf auto-emits `joinProjectResponse` with the rootFolder structure
    when you connect with `?projectId=<id>` on the handshake URL. We do the
    HTTP handshake + WebSocket upgrade + read one message, then close.
    """
    import asyncio
    import json
    try:
        import websockets
    except ImportError:
        return fail("websockets package is required for push")

    async def _run() -> ToolResult[dict[str, Any]]:
        # 1. HTTP handshake (sets GCLB session-affinity cookie on session)
        try:
            hs = session.get(
                "https://www.overleaf.com/socket.io/1/",
                params={"projectId": project_id},
                timeout=15,
            )
        except requests.RequestException as err:
            return fail(f"socket.io handshake failed: {err}")
        if hs.status_code != 200 or ":" not in hs.text:
            return fail(f"socket.io handshake returned {hs.status_code}: {hs.text[:200]!r}")
        sid = hs.text.split(":", 1)[0]

        # 2. WebSocket upgrade
        cookie_header = "; ".join(f"{c.name}={c.value}" for c in session.cookies)
        url = f"wss://www.overleaf.com/socket.io/1/websocket/{sid}"
        try:
            async with websockets.connect(
                url,
                additional_headers={
                    "Cookie": cookie_header,
                    "Origin": "https://www.overleaf.com",
                    "User-Agent": _USER_AGENT,
                },
                open_timeout=15,
            ) as ws:
                # 3. Read until we see joinProjectResponse
                try:
                    async with asyncio.timeout(10):
                        while True:
                            msg = await ws.recv()
                            if isinstance(msg, str) and msg.startswith("5:::"):
                                try:
                                    ev = json.loads(msg[4:])
                                except json.JSONDecodeError:
                                    continue
                                if ev.get("name") == "joinProjectResponse":
                                    args = ev.get("args") or []
                                    if args:
                                        return ok(args[0].get("project", {}))
                except TimeoutError:
                    return fail("timed out waiting for joinProjectResponse")
        except Exception as err:  # noqa: BLE001
            return fail(f"websocket connect failed: {err}")
        return fail("no joinProjectResponse received")

    try:
        return asyncio.run(_run())
    except RuntimeError as err:
        # Running event loop → fall back to a thread-based runner
        if "asyncio.run()" in str(err):
            import concurrent.futures

            def _run_thread() -> ToolResult[dict[str, Any]]:
                return asyncio.new_event_loop().run_until_complete(_run())
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                return ex.submit(_run_thread).result()
        return fail(f"asyncio error: {err}")


def _upload_single_file(
    session: requests.Session,
    project_id: str,
    csrf: str,
    folder_id: str,
    remote_name: str,
    content: bytes,
) -> tuple[bool, str]:
    """POST one file to Overleaf's upload endpoint. Returns (ok, message)."""
    try:
        resp = session.post(
            _UPLOAD_URL.format(project_id),
            params={"folder_id": folder_id, "_csrf": csrf},
            data={"name": remote_name, "relativePath": "null"},
            files={"qqfile": (remote_name, content, "application/octet-stream")},
            headers={
                "X-Csrf-Token": csrf,
                "Origin": "https://www.overleaf.com",
                "Referer": _EDITOR_URL.format(project_id),
                "X-Requested-With": "XMLHttpRequest",
            },
            timeout=60,
        )
    except requests.RequestException as err:
        return False, f"network error: {err}"
    if resp.status_code != 200:
        return False, f"{resp.status_code} {resp.text[:200]}"
    try:
        payload = resp.json()
    except ValueError:
        return False, f"non-JSON response: {resp.text[:200]}"
    if not payload.get("success"):
        return False, str(payload)
    return True, str(payload.get("entity_id") or "")


def olsync_push(
    project_root: Path,
    project_name: str | None = None,
    cookie_path: str | None = None,
) -> ToolResult[dict[str, Any]]:
    """Push every non-excluded file in project_root to the named Overleaf project.

    Uploads one file at a time via Overleaf's `POST /project/{id}/upload`
    endpoint, which overwrites existing documents with the same name in the
    target folder. Only top-level files are supported in this release;
    subdirectories are skipped with a warning (TODO: recursive folder create).
    """
    if not project_name:
        return fail(
            "project_name is required",
            "Pass project_name, or set OVERLEAF_PROJECT_NAME in the MCP env.",
        )

    auth_r = _load_auth(cookie_path, project_root)
    if not auth_r.ok:
        return auth_r

    # Build an HTTP session carrying the cookie
    session = requests.Session()
    session.cookies.update(auth_r.data["cookie"])
    session.headers.update({"User-Agent": _USER_AGENT})

    # Resolve project by name → id
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
    project_id = project["_id"]

    # Get fresh CSRF
    csrf_r = _fetch_fresh_csrf(session, project_id)
    if not csrf_r.ok:
        return csrf_r
    csrf = csrf_r.data

    # Get project tree to find root folder id (needed for upload target)
    tree_r = _fetch_project_tree(session, project_id)
    if not tree_r.ok:
        return tree_r
    root_folders = tree_r.data.get("rootFolder") or []
    if not root_folders:
        return fail("project has no rootFolder — cannot determine upload target")
    root_folder_id = root_folders[0]["_id"]

    # Walk local files and upload top-level ones
    uploaded: list[dict[str, str]] = []
    skipped_nested: list[str] = []
    errors: list[dict[str, str]] = []
    abs_root = project_root.resolve()
    for path in sorted(abs_root.iterdir()):
        if not path.is_file():
            # Subdirectories are deferred until we support folder creation.
            if path.is_dir() and path.name not in _PUSH_EXCLUDE_DIRS:
                skipped_nested.append(path.name + "/")
            continue
        if path.name in _PUSH_EXCLUDE_FILES:
            continue
        content = path.read_bytes()
        ok_flag, msg = _upload_single_file(
            session, project_id, csrf, root_folder_id, path.name, content
        )
        if ok_flag:
            uploaded.append({"file": path.name, "entity_id": msg})
        else:
            errors.append({"file": path.name, "error": msg})

    if errors:
        return fail(
            f"partial push: {len(uploaded)} ok, {len(errors)} failed",
            f"First errors: {errors[:5]}",
        )
    return ok(
        {
            "action": "push",
            "project_name": project_name,
            "project_id": project_id,
            "files_uploaded": len(uploaded),
            "uploaded": uploaded,
            "skipped_nested_dirs": skipped_nested,
        }
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
