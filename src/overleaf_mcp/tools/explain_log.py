"""Parse LaTeX log text into structured errors with suggestions."""
import re
from typing import Any

from overleaf_mcp.types import ToolResult, ok

ErrorKind = str

_SUGGESTIONS: dict[str, str] = {
    "undefined_control_sequence": (
        "Likely a typo in a command, or a missing \\usepackage. Check spelling; "
        "if it's a valid command from a package, add the package to your preamble."
    ),
    "missing_dollar": (
        "Math content appears outside $...$. Wrap the expression in $...$ or use \\(...\\). "
        "Common cause: using _ or ^ in text mode."
    ),
    "file_not_found": (
        "The listed file or package is not installed or path is wrong. Check \\usepackage "
        "spelling, install the package via your TeX distribution, or verify \\input path."
    ),
    "package_error": (
        "A package signaled an error. Read the package's message for the specific cause."
    ),
    "dimension_too_large": (
        "A computed length is out of range. Common cause: \\includegraphics width "
        "wider than \\textwidth, or malformed length arithmetic."
    ),
    "extra_brace": (
        "Unmatched } in source. Check the surrounding lines for an extra or missing brace."
    ),
    "other": "Unrecognized error; see raw log line for context.",
}

_FILE_LINE_RE = re.compile(r"^(.+?):(\d+):\s*(.+)$")


def _classify(msg: str) -> str:
    m = msg.lower()
    if "undefined control sequence" in m:
        return "undefined_control_sequence"
    if "missing $" in m:
        return "missing_dollar"
    if "file" in m and "not found" in m:
        return "file_not_found"
    if "extra }" in m or "extra \\endgroup" in m:
        return "extra_brace"
    if "dimension too large" in m:
        return "dimension_too_large"
    if m.startswith("package ") and " error" in m:
        return "package_error"
    return "other"


def explain_log(log_text: str) -> ToolResult[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for raw in log_text.splitlines():
        line = raw.rstrip()
        fl = _FILE_LINE_RE.match(line)
        if fl:
            kind = _classify(fl.group(3))
            if kind == "other":
                continue
            errors.append(
                {
                    "kind": kind,
                    "file": fl.group(1),
                    "line": int(fl.group(2)),
                    "raw": line,
                    "suggestion": _SUGGESTIONS[kind],
                }
            )
            continue
        if re.match(r"^! LaTeX Error:.*File `.+' not found", line):
            errors.append({"kind": "file_not_found", "raw": line, "suggestion": _SUGGESTIONS["file_not_found"]})
            continue
        if line.startswith("! Undefined control sequence"):
            errors.append({"kind": "undefined_control_sequence", "raw": line, "suggestion": _SUGGESTIONS["undefined_control_sequence"]})
            continue
        if re.match(r"^! Missing \$", line):
            errors.append({"kind": "missing_dollar", "raw": line, "suggestion": _SUGGESTIONS["missing_dollar"]})
            continue
        if line.startswith("Overfull \\hbox"):
            warnings.append({"kind": "overfull_hbox", "raw": line})
            continue
        if line.startswith("Underfull \\hbox"):
            warnings.append({"kind": "underfull_hbox", "raw": line})
            continue
        if re.search(r"LaTeX Warning: Reference.*undefined", line):
            warnings.append({"kind": "reference_undefined", "raw": line})
            continue
    return ok({"errors": errors, "warnings": warnings})
