from overleaf_mcp.tools.check_figures import check_figures


def test_flags_missing_caption_label_centering_float():
    src = "\\begin{figure}\n\\includegraphics{a.png}\n\\end{figure}\n"
    r = check_figures("f.tex", src)
    assert r.ok is True
    codes = {f["code"] for f in r.data}
    assert {"FIG_NO_CAPTION", "FIG_NO_LABEL", "FIG_NO_CENTERING", "FIG_NO_FLOAT_SPEC"} <= codes


def test_clean_figure_has_no_findings():
    src = (
        "\\begin{figure}[htbp]\n"
        "\\centering\n"
        "\\includegraphics[width=0.5\\textwidth]{a.png}\n"
        "\\caption{A figure.}\n"
        "\\label{fig:a}\n"
        "\\end{figure}\n"
    )
    r = check_figures("f.tex", src)
    assert r.ok is True
    assert r.data == []


def test_flags_oversized_width():
    src = (
        "\\begin{figure}[htbp]\n\\centering\n"
        "\\includegraphics[width=2\\textwidth]{a.png}\n"
        "\\caption{x}\\label{f:x}\n\\end{figure}\n"
    )
    r = check_figures("f.tex", src)
    assert r.ok is True
    assert any(f["code"] == "FIG_WIDTH_SUSPICIOUS" for f in r.data)
