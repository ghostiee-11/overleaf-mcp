# overleaf-mcp

Model Context Protocol server for LaTeX and Overleaf projects. Give Claude Code, GitHub Copilot, Google Antigravity, or any MCP-compatible AI the ability to read, format, lint, compile, and sync your LaTeX work.

## Install

### The MCP server (Python 3.11+)

```bash
# Run without installing
uvx overleaf-mcp

# Or install persistently
pipx install overleaf-mcp
```

### LaTeX tools (optional, unlocks more features)

The MCP starts with whatever tools are present. Install what you want:

| Tool | Unlocks | macOS | Ubuntu/Debian | Windows |
|---|---|---|---|---|
| `latexindent` | formatting | `brew install latexindent` | `apt install texlive-extra-utils` | bundled with MikTeX / TeX Live |
| `chktex` | linting | `brew install chktex` | `apt install chktex` | bundled |
| `latexmk` | compiling | `brew install --cask mactex` (full) | `apt install latexmk` | bundled |

Or install everything at once: `brew install --cask mactex` (macOS) / `apt install texlive-full` (Debian).

## MCP client configuration

### Claude Code

Edit `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "overleaf": {
      "command": "uvx",
      "args": ["overleaf-mcp"],
      "env": {
        "OVERLEAF_PROJECT_ROOT": "/absolute/path/to/project"
      }
    }
  }
}
```

### GitHub Copilot (with MCP support)

Same block in `.vscode/mcp.json` or the global Copilot MCP settings.

### Google Antigravity / other MCP clients

Any client that speaks the MCP stdio transport works — adjust the config path per the client's docs.

## Modes

- **Local** (default): set `OVERLEAF_PROJECT_ROOT`. Works offline. Free for everyone.
- **Overleaf-synced** (Overleaf Premium): also set `OVERLEAF_GIT_URL` and `OVERLEAF_GIT_TOKEN`. Enables `pull_from_overleaf` / `push_to_overleaf`.
- **ZIP-bridge** (free-tier round-trip): use `import_overleaf_zip` / `export_overleaf_zip` with Overleaf's **Download → Source** and **Upload Project**.

## Tools

**File/project**
- `detect_capabilities`, `list_tex_files`, `read_tex_file`, `write_tex_file`, `get_project_structure`

**Formatting & linting**
- `format_file`, `format_snippet`, `check_formatting` (wraps `latexindent`)
- `lint_file` (wraps `chktex`)

**Static checks**
- `check_math`, `check_figures`, `check_table`, `suggest_table_fix`
- `check_packages`, `check_consistency`, `find_unused_labels_and_refs`

**Compile**
- `compile` (wraps `latexmk`)
- `explain_log` (parses any LaTeX log into structured errors)

**Overleaf sync (Premium)**
- `pull_from_overleaf`, `push_to_overleaf`, `overleaf_status`

**ZIP bridge (free-tier)**
- `import_overleaf_zip`, `export_overleaf_zip`

## Free-tier round-trip

1. Overleaf project → **Menu → Download → Source** (zip).
2. Agent: `import_overleaf_zip {"zip_path": "/path/to/download.zip"}`.
3. Agent uses format/lint/check tools on the local copy.
4. Agent: `export_overleaf_zip {"out_path": "/tmp/out.zip"}`.
5. Overleaf → **New Project → Upload Project** → choose the zip.

## Security

- Every path tool validates that the target is inside `OVERLEAF_PROJECT_ROOT`.
- Git tokens are injected via `GIT_ASKPASS` — never placed in URLs, argv, or logs.
- ZIP extraction rejects entries that escape the root (zip-slip) or use absolute paths.
- Subprocess calls use `shell=False` with argv lists — no string concatenation.

## License

MIT.
