from overleaf_mcp.capability import detect_capabilities, reset_capability_cache


def setup_function():
    reset_capability_cache()


def test_returns_all_keys():
    caps = detect_capabilities()
    assert set(caps.keys()) == {"latexindent", "chktex", "latexmk", "ols"}
    for cap in caps.values():
        assert isinstance(cap.available, bool)
        if not cap.available:
            assert isinstance(cap.suggestion, str)
            assert len(cap.suggestion) > 0


def test_caches_results():
    reset_capability_cache()
    a = detect_capabilities()
    b = detect_capabilities()
    assert a is b
