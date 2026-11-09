def test_errors():
    from main import run_tool

    assert run_tool({"tool": "divide", "args": {}}) == "Error: unknown tool 'divide'"
    got = run_tool({"tool": "add", "args": {"a": 1}})
    assert isinstance(got, str) and got.startswith("Error: "), f"got {got!r}"
    assert run_tool({"tool": "multiply", "args": {"a": 6, "b": 7}}) == 42
