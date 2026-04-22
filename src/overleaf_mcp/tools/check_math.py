"""Static checks for LaTeX math blocks."""
import re

from overleaf_mcp.checks.findings import Finding
from overleaf_mcp.parse import Environment, MathBlock, tokenize
from overleaf_mcp.types import ToolResult, ok

_ALIGN_ENVS = {"align", "align*", "aligned", "array", "matrix", "pmatrix", "bmatrix"}
_LEFT = re.compile(r"\\left\b")
_RIGHT = re.compile(r"\\right\b")
_AMP = re.compile(r"(?<!\\)&")


def check_math(file: str, content: str) -> ToolResult[list[dict]]:
    findings: list[Finding] = []
    for tok in tokenize(content):
        if isinstance(tok, MathBlock):
            left_n = len(_LEFT.findall(tok.body))
            right_n = len(_RIGHT.findall(tok.body))
            if left_n != right_n:
                findings.append(
                    Finding(
                        file=file,
                        line=tok.start_line,
                        code="MATH_LEFT_RIGHT_UNPAIRED",
                        message=f"\\left count ({left_n}) != \\right count ({right_n}) in math block",
                        severity="error",
                    )
                )
            stripped = re.sub(r"\\left\s*[({\[]", "", tok.body)
            stripped = re.sub(r"\\right\s*[)}\]]", "", stripped)
            stripped = re.sub(r"\\[{}]", "", stripped)
            counts = {ch: stripped.count(ch) for ch in "()[]{}"}
            if (
                counts["("] != counts[")"]
                or counts["["] != counts["]"]
                or counts["{"] != counts["}"]
            ):
                findings.append(
                    Finding(
                        file=file,
                        line=tok.start_line,
                        code="MATH_BRACKET_UNBALANCED",
                        message=(
                            f"Unbalanced brackets: parens {counts['(']}/{counts[')']}, "
                            f"squares {counts['[']}/{counts[']']}, "
                            f"braces {counts['{']}/{counts['}']}"
                        ),
                        severity="error",
                    )
                )
        elif isinstance(tok, Environment) and tok.name in _ALIGN_ENVS:
            rows = [r.strip() for r in tok.body.split("\\\\") if r.strip()]
            amp_counts = [len(_AMP.findall(r)) for r in rows]
            if amp_counts and any(n != amp_counts[0] for n in amp_counts):
                findings.append(
                    Finding(
                        file=file,
                        line=tok.start_line,
                        code="MATH_ALIGN_COLUMN_DRIFT",
                        message=f"Column count differs across rows in {tok.name}: {amp_counts}",
                        severity="warning",
                    )
                )
    return ok([f.to_dict() for f in findings])
