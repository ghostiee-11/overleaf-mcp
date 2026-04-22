from overleaf_mcp.types import ToolResult, ok, fail


def test_ok_produces_success_result():
    r: ToolResult[int] = ok(42)
    assert r.ok is True
    assert r.data == 42
    assert r.error is None
    assert r.suggestion is None


def test_fail_with_suggestion():
    r = fail("nope", "try harder")
    assert r.ok is False
    assert r.error == "nope"
    assert r.suggestion == "try harder"
    assert r.data is None


def test_fail_without_suggestion():
    r = fail("nope")
    assert r.ok is False
    assert r.error == "nope"
    assert r.suggestion is None


def test_tool_result_serializes_to_json():
    r = ok({"x": 1})
    j = r.model_dump_json()
    assert '"ok":true' in j
    assert '"x":1' in j
