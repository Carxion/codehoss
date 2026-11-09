def test_counts_the(run_program):
    lines = run_program(["The cat saw the dog"]).lines
    assert "the: 2" in lines, f"Expected a line 'the: 2' in {lines}"
