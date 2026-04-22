"""Static checks for tabular environments."""
import re

from overleaf_mcp.checks.findings import Finding
from overleaf_mcp.parse import Environment, tokenize
from overleaf_mcp.types import ToolResult, ok

_SPEC_EXTRACT = re.compile(r"\\begin\{[^}]+\}(?:\[[^\]]*\])?\{([^}]+)\}")
_AMP = re.compile(r"(?<!\\)&")


def _count_spec_columns(spec: str) -> int:
    i, n = 0, 0
    while i < len(spec):
        ch = spec[i]
        if ch in ("l", "c", "r", "X"):
            n += 1
            i += 1
        elif ch in ("p", "m", "b"):
            n += 1
            close = spec.find("}", i)
            i = close + 1 if close >= 0 else i + 1
        elif ch in ("@", "!"):
            close = spec.find("}", i)
            i = close + 1 if close >= 0 else i + 1
        else:
            i += 1
    return n


def _parse_rows(body: str) -> list[list[str]]:
    raw_rows = [r.strip() for r in body.split("\\\\") if r.strip()]
    rows: list[list[str]] = []
    for r in raw_rows:
        if re.match(r"^\\hline\b", r):
            continue
        rows.append([c.strip() for c in _AMP.split(r)])
    return rows


def check_table(file: str, content: str) -> ToolResult[list[dict]]:
    findings: list[Finding] = []
    for tok in tokenize(content):
        if not (isinstance(tok, Environment) and tok.name in ("tabular", "tabularx", "array")):
            continue
        begin_marker = f"\\begin{{{tok.name}}}"
        idx = content.find(begin_marker)
        spec = ""
        if idx >= 0:
            m = _SPEC_EXTRACT.match(content[idx:])
            if m:
                spec = m.group(1)
        expected = _count_spec_columns(spec)
        for i, row in enumerate(_parse_rows(tok.body)):
            if len(row) != expected:
                findings.append(
                    Finding(
                        file=file,
                        line=tok.start_line + i,
                        code="TABLE_COL_MISMATCH",
                        message=(
                            f'row {i + 1} has {len(row)} cells but column spec "{spec}" declares {expected}'
                        ),
                        severity="error",
                    )
                )
    return ok([f.to_dict() for f in findings])


def suggest_table_fix(file: str, content: str) -> ToolResult[dict]:
    for tok in tokenize(content):
        if isinstance(tok, Environment) and tok.name == "tabular":
            rows = _parse_rows(tok.body)
            widest = max((len(r) for r in rows), default=0)
            return ok(
                {
                    "suggested_spec": "l" * widest,
                    "reason": f'widest row has {widest} cells; use "{"l" * widest}" or adjust rows',
                }
            )
    return ok({"suggested_spec": "", "reason": "no tabular env found"})
