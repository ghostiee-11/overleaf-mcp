from pathlib import Path

from overleaf_mcp.tools.check_math import check_math

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "checks"


def test_flags_unpaired_and_unbalanced_and_column_drift():
    content = (FIX / "math_bad.tex").read_text()
    r = check_math("math_bad.tex", content)
    assert r.ok is True
    codes = {f["code"] for f in r.data}
    assert "MATH_LEFT_RIGHT_UNPAIRED" in codes
    assert "MATH_BRACKET_UNBALANCED" in codes
    assert "MATH_ALIGN_COLUMN_DRIFT" in codes


def test_clean_math_has_no_findings():
    src = "\\begin{document}$\\left( \\frac{a}{b} \\right)$\\end{document}"
    r = check_math("ok.tex", src)
    assert r.ok is True
    assert r.data == []
