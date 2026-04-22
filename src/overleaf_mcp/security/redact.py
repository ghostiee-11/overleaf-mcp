"""Replace sensitive tokens in strings before logging or returning to callers."""


def redact(text: str, token: str | None) -> str:
    if not token:
        return text
    return text.replace(token, "<REDACTED>")
