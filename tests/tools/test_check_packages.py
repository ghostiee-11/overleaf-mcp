from overleaf_mcp.tools.check_packages import check_packages


def test_flags_duplicate_usepackage():
    src = "\\usepackage{amsmath}\n\\usepackage{amsmath}\n"
    r = check_packages("p.tex", src)
    assert r.ok is True
    assert any(f["code"] == "PKG_DUPLICATE" for f in r.data)


def test_flags_subfig_subcaption_conflict():
    src = "\\usepackage{subfig}\n\\usepackage{subcaption}\n"
    r = check_packages("p.tex", src)
    assert r.ok is True
    assert any(f["code"] == "PKG_CONFLICT" for f in r.data)


def test_flags_missing_package_for_command():
    src = "\\documentclass{article}\n\\begin{document}\\SI{5}{\\metre}\\end{document}\n"
    r = check_packages("p.tex", src)
    assert r.ok is True
    assert any(f["code"] == "PKG_MISSING_FOR_CMD" for f in r.data)


def test_flags_hyperref_after_cleveref():
    src = "\\usepackage{cleveref}\n\\usepackage{hyperref}\n"
    r = check_packages("p.tex", src)
    assert r.ok is True
    assert any(f["code"] == "PKG_LOAD_ORDER" for f in r.data)
