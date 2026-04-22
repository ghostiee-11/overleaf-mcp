from pathlib import Path

from overleaf_mcp.server import build_server


def test_local_mode_has_base_tools_and_zip_but_not_sync(tmp_path: Path):
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
        # ZIP bridge — always present
        "import_overleaf_zip",
        "export_overleaf_zip",
    }
    assert expected.issubset(set(tool_names))
    # Git sync tools must NOT be present in local mode
    for sync_tool in ("pull_from_overleaf", "push_to_overleaf", "overleaf_status"):
        assert sync_tool not in tool_names, f"{sync_tool!r} should not be registered in local mode"


def test_synced_mode_exposes_sync_tools(tmp_path: Path):
    env = {
        "OVERLEAF_PROJECT_ROOT": str(tmp_path),
        "OVERLEAF_GIT_URL": "https://git.overleaf.com/x",
        "OVERLEAF_GIT_TOKEN": "tok",
    }
    server, config, tool_names = build_server(env)
    assert server is not None
    assert config.mode == "synced"
    for sync_tool in ("pull_from_overleaf", "push_to_overleaf", "overleaf_status"):
        assert sync_tool in tool_names, f"{sync_tool!r} should be registered in synced mode"
    # ZIP bridge still present in synced mode
    assert "import_overleaf_zip" in tool_names
    assert "export_overleaf_zip" in tool_names
