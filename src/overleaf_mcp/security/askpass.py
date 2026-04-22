"""Inject a git token via GIT_ASKPASS without placing it in argv or URLs."""
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


@contextmanager
def git_auth_env(token: str) -> Iterator[dict[str, str]]:
    """
    Yield an env dict containing GIT_ASKPASS that points at a freshly-written
    shell script echoing the token from a 0600 temp file. Both are wiped when
    the context exits.
    """
    tmpdir = Path(tempfile.mkdtemp(prefix="olmcp-askpass-"))
    try:
        token_file = tmpdir / "token"
        token_file.write_text(token)
        token_file.chmod(0o600)

        script = tmpdir / "askpass.sh"
        script.write_text(f'#!/bin/sh\ncat "{token_file}"\n')
        script.chmod(0o700)

        env = {
            **os.environ,
            "GIT_ASKPASS": str(script),
            "GIT_TERMINAL_PROMPT": "0",
        }
        yield env
    finally:
        try:
            for p in tmpdir.iterdir():
                try:
                    p.unlink()
                except OSError:
                    pass
            tmpdir.rmdir()
        except OSError:
            pass
