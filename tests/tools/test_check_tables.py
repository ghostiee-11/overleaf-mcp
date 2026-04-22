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


def test_booktabs_rules_do_not_count_as_rows():
    # \toprule, \midrule, \bottomrule are rules, not table rows.
    src = (
        "\\begin{tabular}{lrr}\n"
        "\\toprule\n"
        "Method & A & B \\\\\n"
        "\\midrule\n"
        "One & 1 & 2 \\\\\n"
        "Two & 3 & 4 \\\\\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
    )
    r = check_table("t.tex", src)
    assert r.ok is True
    assert r.data == []


def test_hline_still_does_not_count_as_row():
    src = (
        "\\begin{tabular}{ll}\n"
        "\\hline\n"
        "a & b \\\\\n"
        "\\hline\n"
        "c & d \\\\\n"
        "\\hline\n"
        "\\end{tabular}\n"
    )
    r = check_table("t.tex", src)
    assert r.ok is True
    assert r.data == []
