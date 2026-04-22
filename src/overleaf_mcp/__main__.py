"""CLI entry point: python -m overleaf_mcp (or `overleaf-mcp` via console script)."""
import os
import sys

from overleaf_mcp.capability import detect_capabilities
from overleaf_mcp.server import ConfigError, build_server


def main() -> int:
    try:
        server, config, _ = build_server(os.environ)
    except ConfigError as err:
        print(f"[overleaf-mcp] config error: {err}", file=sys.stderr)
        return 1
    for name, cap in detect_capabilities().items():
        if cap.available:
            print(f"[overleaf-mcp] {name}: {cap.version}", file=sys.stderr)
        else:
            print(f"[overleaf-mcp] {name} not found. {cap.suggestion or ''}", file=sys.stderr)
    print(
        f"[overleaf-mcp] mode={config.mode} root={config.project_root}", file=sys.stderr
    )
    server.run()  # stdio transport by default
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
