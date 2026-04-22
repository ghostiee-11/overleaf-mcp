# Contributing

## Dev setup

```bash
git clone <repo>
cd overleaf-mcp
uv sync --extra dev
uv run pytest              # run all tests
uv run pytest tests/golden # golden corpus
uv run ruff check .        # lint
```

## Running tests with real LaTeX tools

Install `latexindent` / `chktex` / `latexmk`, then just run `uv run pytest`. Tests that need those binaries detect them via `shutil.which()` and skip with a message when missing.

## Manual Overleaf sync smoke test

(Cannot be automated in CI; requires real Overleaf credentials.)

1. Create a scratch Overleaf project.
2. Enable Git Integration in Overleaf account settings, generate a token.
3. Point the MCP at an empty local dir with `OVERLEAF_GIT_URL` / `OVERLEAF_GIT_TOKEN` set.
4. From an MCP client, call `pull_from_overleaf`. Expected: project files appear locally.
5. Edit a file via `write_tex_file`, then `push_to_overleaf`. Expected: change visible in Overleaf UI.

## Release process

1. `uv run ruff check . && uv run pytest`
2. Bump `version` in `pyproject.toml` and update CHANGELOG if present.
3. `git tag vX.Y.Z && git push --tags`
4. Maintainer only: `uv build && uv publish` (or `python -m twine upload dist/*`). Always `uv build` first and inspect `dist/` before publishing.
