def test_runs():
    from main import run_tool

    assert run_tool({"tool": "add", "args": {"a": 2, "b": 3}}) == 5
