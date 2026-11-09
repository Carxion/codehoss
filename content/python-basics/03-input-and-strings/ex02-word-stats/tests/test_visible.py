def test_prints_upper(run_program):
    lines = run_program(["python"]).lines
    assert "Upper: PYTHON" in lines, f"Expected a line 'Upper: PYTHON' in {lines}"
