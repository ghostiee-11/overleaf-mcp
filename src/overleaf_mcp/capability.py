"""Detect which LaTeX binaries are installed."""
import shutil
import subprocess
from dataclasses import dataclass

_INSTALL_HINTS: dict[str, str] = {
    "latexindent": "Install via TeX Live or `brew install latexindent` (macOS).",
    "chktex": "Comes with TeX Live; on Debian/Ubuntu: `apt install chktex`.",
    "latexmk": "Comes with TeX Live; on macOS: `brew install --cask mactex`.",
    "ols": (
        "overleaf-sync gives free-tier users bi-directional Overleaf sync. "
        "Install with `uv tool install overleaf-sync` or `pipx install overleaf-sync`, "
        "then run `ols login` once to authenticate."
    ),
}


@dataclass(frozen=True)
class Capability:
    available: bool
    version: str | None = None
    suggestion: str | None = None


_cache: dict[str, Capability] | None = None


def _probe(binary: str, version_arg: str) -> Capability:
    if shutil.which(binary) is None:
        return Capability(available=False, suggestion=_INSTALL_HINTS.get(binary))
    try:
        result = subprocess.run(
            [binary, version_arg],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        first_line = (result.stdout or result.stderr).splitlines()[0].strip() if (result.stdout or result.stderr) else None
        return Capability(available=True, version=first_line)
    except (subprocess.TimeoutExpired, OSError):
        return Capability(available=False, suggestion=_INSTALL_HINTS.get(binary))


def detect_capabilities() -> dict[str, Capability]:
    """Probe for LaTeX binaries. Cached; call `reset_capability_cache()` to re-probe."""
    global _cache
    if _cache is not None:
        return _cache
    _cache = {
        "latexindent": _probe("latexindent", "--version"),
        "chktex": _probe("chktex", "--version"),
        "latexmk": _probe("latexmk", "-v"),
        "ols": _probe("ols", "--version"),
    }
    return _cache


def reset_capability_cache() -> None:
    """For tests."""
    global _cache
    _cache = None
