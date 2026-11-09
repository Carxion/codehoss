def test_sizes(run_program):
    scores = run_program().vars.get("scores")
    assert sorted(scores) == [2, 8, 64], f"scores has keys {sorted(scores)}"
