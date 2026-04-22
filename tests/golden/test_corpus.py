"""Run every non-mutating check against every corpus project and compare to baseline."""
import json
from collections import Counter
from pathlib import Path

import pytest

from overleaf_mcp.tools.check_consistency import check_consistency
from overleaf_mcp.tools.check_figures import check_figures
from overleaf_mcp.tools.check_math import check_math
from overleaf_mcp.tools.check_packages import check_packages
from overleaf_mcp.tools.check_refs import find_unused_labels_and_refs
from overleaf_mcp.tools.check_tables import check_table
from overleaf_mcp.tools.files import list_tex_files, read_tex_file

GOLDEN = Path(__file__).resolve().parent
BASELINES = GOLDEN / "baselines"
PROJECTS = ["article", "thesis", "beamer", "multi-file"]


def _counts(findings: list[dict]) -> dict[str, int]:
    return dict(Counter(f["code"] for f in findings))


def _per_file(project_root: Path, check):
    list_r = list_tex_files(project_root)
    assert list_r.ok
    acc: list[dict] = []
    for rel in [f for f in list_r.data if f.endswith(".tex")]:
        rf = read_tex_file(project_root, rel)
        assert rf.ok
        r = check(rel, rf.data["content"])
        assert r.ok
        acc.extend(r.data)
    return acc


@pytest.mark.parametrize("name", PROJECTS)
def test_golden_corpus_matches_baselines(name: str):
    project_root = GOLDEN / name
    baseline = json.loads(
        (BASELINES / f"{name}.json").read_text()
    )

    assert _counts(_per_file(project_root, check_math)) == baseline.get("check_math", {})
    assert _counts(_per_file(project_root, check_figures)) == baseline.get("check_figures", {})
    assert _counts(_per_file(project_root, check_table)) == baseline.get("check_table", {})
    assert _counts(_per_file(project_root, check_packages)) == baseline.get("check_packages", {})
    r = check_consistency(project_root)
    assert r.ok
    assert _counts(r.data) == baseline.get("check_consistency", {})
    r = find_unused_labels_and_refs(project_root)
    assert r.ok
    assert _counts(r.data) == baseline.get("find_unused_labels_and_refs", {})
