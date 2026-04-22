"""Shared Finding dataclass for all static checks."""
from dataclasses import dataclass
from typing import Literal

Severity = Literal["error", "warning", "info"]


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    code: str
    message: str
    severity: Severity
    column: int | None = None

    def to_dict(self) -> dict:
        d: dict = {
            "file": self.file,
            "line": self.line,
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }
        if self.column is not None:
            d["column"] = self.column
        return d
