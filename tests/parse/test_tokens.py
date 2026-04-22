from overleaf_mcp.parse.tokens import Command, Environment, MathBlock, tokenize


def test_finds_environments_with_line_numbers():
    src = "\\documentclass{article}\n\\begin{document}\nhi\n\\end{document}\n"
    toks = tokenize(src)
    envs = [t for t in toks if isinstance(t, Environment)]
    assert len(envs) == 1
    assert envs[0].name == "document"
    assert envs[0].start_line == 2
    assert envs[0].end_line == 4


def test_finds_commands_with_argument():
    src = "\\section{Intro}\n\\label{sec:intro}\n"
    toks = tokenize(src)
    cmds = [t for t in toks if isinstance(t, Command)]
    assert [c.name for c in cmds] == ["section", "label"]
    assert cmds[0].arg == "Intro"


def test_finds_math_blocks():
    src = "inline $x=1$ and display \\[ y=2 \\] end"
    toks = tokenize(src)
    maths = [t for t in toks if isinstance(t, MathBlock)]
    assert len(maths) == 2
    styles = {m.style for m in maths}
    assert styles == {"inline", "display"}


def test_ignores_comments():
    src = "% \\section{ignored}\n\\section{real}\n"
    toks = tokenize(src)
    cmds = [t for t in toks if isinstance(t, Command)]
    assert [c.name for c in cmds] == ["section"]
