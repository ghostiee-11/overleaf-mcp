from overleaf_mcp.security.redact import redact


def test_replaces_token():
    assert redact("before abc123 after", "abc123") == "before <REDACTED> after"


def test_redacts_multiple():
    assert redact("x abc y abc z", "abc") == "x <REDACTED> y <REDACTED> z"


def test_noop_when_token_empty():
    assert redact("x abc y", "") == "x abc y"
    assert redact("x abc y", None) == "x abc y"


def test_redacts_inside_url():
    assert redact("https://user:tok@host/repo", "tok") == "https://user:<REDACTED>@host/repo"
