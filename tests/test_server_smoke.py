from pathlib import Path

from overleaf_mcp.server import build_server


def test_builds_server_with_v0_1_tools(tmp_path: Path):
    server, config, tool_names = build_server({"OVERLEAF_PROJECT_ROOT": str(tmp_path)})
    assert server is not None
    assert config.mode == "local"
    expected = {
        "detect_capabilities",
        "list_tex_files",
        "read_tex_file",
        "write_tex_file",
        "format_file",
        "format_snippet",
        "check_formatting",
        "lint_file",
        "get_project_structure",
        "check_math",
        "check_figures",
        "check_table",
        "suggest_table_fix",
        "check_packages",
        "check_consistency",
        "find_unused_labels_and_refs",
        "compile",
        "explain_log",
    }
    assert expected.issubset(set(tool_names))
