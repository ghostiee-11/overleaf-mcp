# overleaf-mcp

Model Context Protocol server for LaTeX / Overleaf project formatting and linting. Works with Claude Code, GitHub Copilot, Google Antigravity, and any MCP-compatible client.

## Install

Needs Python 3.11+. Easiest launcher is `uv` / `uvx`:

```bash
# Try it without installing globally
uvx overleaf-mcp --help

# Or install with pipx
pipx install overleaf-mcp
```

To use formatting and linting, also install the LaTeX tools:

- macOS: `brew install --cask mactex` (full) or `brew install latexindent chktex` (minimal)
- Debian/Ubuntu: `apt install texlive-extra-utils chktex`
- Windows: install MikTeX or TeX Live

## Configure

Add to your MCP client config (example: Claude Code `~/.claude/mcp.json`):

```json
{
  "mcpServers": {
    "overleaf": {
      "command": "uvx",
      "args": ["overleaf-mcp"],
      "env": {
        "OVERLEAF_PROJECT_ROOT": "/absolute/path/to/your/latex/project"
      }
    }
  }
}
```

## Tools (v0.1)

- `detect_capabilities` — report which LaTeX binaries are available
- `list_tex_files`, `read_tex_file`, `write_tex_file`
- `format_file`, `format_snippet`, `check_formatting` (wraps `latexindent`)
- `lint_file` (wraps `chktex`)

Overleaf git sync, ZIP-bridge, compile, and custom checks arrive in later releases.
