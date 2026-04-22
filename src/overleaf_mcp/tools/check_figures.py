"""Static checks for figure environments."""

import re

from overleaf_mcp.checks.findings import Finding
from overleaf_mcp.parse import Environment, tokenize
from overleaf_mcp.types import ToolResult, ok

_WIDTH_RE = re.compile(r"width\s*=\s*([\d.]+)\\textwidth")
_FLOAT_SPEC_RE = re.compile(r"^\s*\[")


def check_figures(file: str, content: str) -> ToolResult[list[dict]]:
    findings: list[Finding] = []
    for tok in tokenize(content):
        if not (isinstance(tok, Environment) and tok.name in ("figure", "figure*")):
            continue
        body = tok.body
        line = tok.start_line

        if "\\caption" not in body:
            findings.append(
                Finding(
                    file=file,
                    line=line,
                    code="FIG_NO_CAPTION",
                    message="figure has no \\caption",
                    severity="warning",
                )
            )
        if "\\label" not in body:
            findings.append(
                Finding(
                    file=file,
                    line=line,
                    code="FIG_NO_LABEL",
                    message="figure has no \\label",
                    severity="warning",
                )
            )
        if "\\centering" not in body:
            findings.append(
                Finding(
                    file=file,
                    line=line,
                    code="FIG_NO_CENTERING",
                    message="figure missing \\centering",
                    severity="info",
                )
            )

        begin_marker = f"\\begin{{{tok.name}}}"
        idx = content.find(begin_marker)
        if idx >= 0:
            after = content[idx + len(begin_marker) : idx + len(begin_marker) + 20]
            if not _FLOAT_SPEC_RE.match(after):
                findings.append(
                    Finding(
                        file=file,
                        line=line,
                        code="FIG_NO_FLOAT_SPEC",
                        message="figure has no float placement spec like [htbp]",
                        severity="info",
                    )
                )

        wm = _WIDTH_RE.search(body)
        if wm:
            try:
                frac = float(wm.group(1))
            except ValueError:
                frac = 0
            if frac > 1:
                findings.append(
                    Finding(
                        file=file,
                        line=line,
                        code="FIG_WIDTH_SUSPICIOUS",
                        message=f"\\includegraphics width={frac}\\textwidth exceeds page",
                        severity="warning",
                    )
                )

    return ok([f.to_dict() for f in findings])
