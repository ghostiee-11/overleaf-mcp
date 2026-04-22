from pathlib import Path

from overleaf_mcp.tools.check_refs import find_unused_labels_and_refs


def test_detects_dangling_unused_label_and_unused_bib(tmp_path: Path):
    (tmp_path / "main.tex").write_text(
        "\\label{sec:intro}\n"
        "\\label{sec:orphan}\n"
        "See \\ref{sec:intro} and \\ref{sec:missing}.\n"
        "Cited: \\cite{used}.\n"
        "\\bibliography{refs}\n"
    )
    (tmp_path / "refs.bib").write_text(
        "@article{used,title={A}}\n@article{unused,title={B}}\n"
    )
    r = find_unused_labels_and_refs(tmp_path)
    assert r.ok is True
    codes = {f["code"] for f in r.data}
    assert {"REF_DANGLING", "LABEL_UNUSED", "BIB_UNUSED"} <= codes
