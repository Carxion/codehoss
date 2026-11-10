def test_twelve(run_program):
    lines = run_program(["12"]).lines[1:]
    assert lines == [f"12 x {i} = {12 * i}" for i in range(1, 11)]
