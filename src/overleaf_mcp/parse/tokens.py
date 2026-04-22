"""Lightweight TeX tokenizer. Extracts commands, environments, and math blocks."""
import re
from dataclasses import dataclass
from typing import Literal, Union

MathStyle = Literal["inline", "display"]


@dataclass(frozen=True)
class Command:
    name: str
    arg: str | None
    line: int
    col: int


@dataclass(frozen=True)
class Environment:
    name: str
    start_line: int
    end_line: int
    body: str


@dataclass(frozen=True)
class MathBlock:
    style: MathStyle
    start_line: int
    end_line: int
    body: str


Token = Union[Command, Environment, MathBlock]

_COMMENT_RE = re.compile(r"(?<!\\)%[^\n]*")
_ENV_RE = re.compile(r"\\(begin|end)\{([a-zA-Z*]+)\}")
_CMD_RE = re.compile(r"\\([a-zA-Z]+)(?:\{([^{}]*)\})?")
_DISPLAY_RE = re.compile(r"\\\[([\s\S]*?)\\\]")
_INLINE_RE = re.compile(r"(?<!\$)\$(?!\$)([^$\n]+)\$")


def _strip_comments(src: str) -> str:
    return _COMMENT_RE.sub("", src)


def _line_of(src: str, index: int) -> tuple[int, int]:
    line = src.count("\n", 0, index) + 1
    last_nl = src.rfind("\n", 0, index)
    col = index - last_nl if last_nl >= 0 else index + 1
    return line, col


def tokenize(raw: str) -> list[Token]:
    src = _strip_comments(raw)
    tokens: list[Token] = []

    stack: list[tuple[str, int, int]] = []
    for m in _ENV_RE.finditer(src):
        kind, name = m.group(1), m.group(2)
        start_line, _ = _line_of(src, m.start())
        if kind == "begin":
            stack.append((name, m.end(), start_line))
        else:
            for i in range(len(stack) - 1, -1, -1):
                if stack[i][0] == name:
                    body_start = stack[i][1]
                    open_line = stack[i][2]
                    end_line, _ = _line_of(src, m.start())
                    tokens.append(
                        Environment(
                            name=name,
                            start_line=open_line,
                            end_line=end_line,
                            body=src[body_start : m.start()],
                        )
                    )
                    del stack[i]
                    break

    for m in _CMD_RE.finditer(src):
        name = m.group(1)
        if name in ("begin", "end"):
            continue
        line, col = _line_of(src, m.start())
        tokens.append(Command(name=name, arg=m.group(2), line=line, col=col))

    for m in _DISPLAY_RE.finditer(src):
        start_line, _ = _line_of(src, m.start())
        end_line, _ = _line_of(src, m.end())
        tokens.append(MathBlock(style="display", start_line=start_line, end_line=end_line, body=m.group(1)))

    for m in _INLINE_RE.finditer(src):
        start_line, _ = _line_of(src, m.start())
        end_line, _ = _line_of(src, m.end())
        tokens.append(MathBlock(style="inline", start_line=start_line, end_line=end_line, body=m.group(1)))

    return tokens
