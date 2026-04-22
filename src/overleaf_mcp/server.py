"""Build the FastMCP server and register v0.1 tools."""
from typing import Mapping

from mcp.server.fastmcp import FastMCP

from overleaf_mcp.capability import detect_capabilities
from overleaf_mcp.config import Config, load_config
from overleaf_mcp.tools.files import list_tex_files, read_tex_file, write_tex_file
from overleaf_mcp.tools.format import check_formatting, format_file, format_snippet
from overleaf_mcp.tools.lint import lint_file


class ConfigError(RuntimeError):
    pass


def build_server(env: Mapping[str, str]) -> tuple[FastMCP, Config, list[str]]:
    cfg_result = load_config(env)
    if not cfg_result.ok:
        raise ConfigError(
            f"{cfg_result.error}"
            + (f" — {cfg_result.suggestion}" if cfg_result.suggestion else "")
        )
    config = cfg_result.data
    server = FastMCP("overleaf-mcp")
    tool_names: list[str] = []

    def _register(name: str, description: str):
        def decorator(fn):
            tool_names.append(name)
            return server.tool(name=name, description=description)(fn)
        return decorator

    @_register("detect_capabilities", "Report which LaTeX binaries are available.")
    def _detect_capabilities() -> dict:
        return {k: v.__dict__ for k, v in detect_capabilities().items()}

    @_register("list_tex_files", "List .tex/.bib/.cls/.sty files in the project.")
    def _list_tex_files() -> dict:
        return list_tex_files(config.project_root).model_dump()

    @_register("read_tex_file", "Read a .tex file; returns content and line count.")
    def _read_tex_file(path: str) -> dict:
        return read_tex_file(config.project_root, path).model_dump()

    @_register("write_tex_file", "Atomically write content to a file.")
    def _write_tex_file(path: str, content: str) -> dict:
        return write_tex_file(config.project_root, path, content).model_dump()

    @_register("format_file", "Run latexindent on a file, modifying it in place.")
    def _format_file(path: str) -> dict:
        return format_file(config.project_root, path).model_dump()

    @_register("format_snippet", "Format a LaTeX snippet without touching disk.")
    def _format_snippet(code: str) -> dict:
        return format_snippet(code).model_dump()

    @_register("check_formatting", "Dry-run latexindent; return unified diff.")
    def _check_formatting(path: str) -> dict:
        return check_formatting(config.project_root, path).model_dump()

    @_register("lint_file", "Run chktex; return structured warnings.")
    def _lint_file(path: str) -> dict:
        return lint_file(config.project_root, path).model_dump()

    return server, config, tool_names
