from overleaf_mcp.tools.check_tables import check_table, suggest_table_fix

BAD = "\\begin{tabular}{ll}\na & b & c \\\\\nd & e \\\\\n\\end{tabular}\n"
GOOD = "\\begin{tabular}{lll}\na & b & c \\\\\nd & e & f \\\\\n\\end{tabular}\n"


def test_flags_column_count_mismatch():
    r = check_table("t.tex", BAD)
    assert r.ok is True
    assert any(f["code"] == "TABLE_COL_MISMATCH" for f in r.data)


def test_consistent_table_has_no_findings():
    r = check_table("t.tex", GOOD)
    assert r.ok is True
    assert r.data == []


def test_suggest_fix_matches_widest_row():
    r = suggest_table_fix("t.tex", BAD)
    assert r.ok is True
    assert r.data["suggested_spec"] == "lll"
