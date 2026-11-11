def test_no_spaces_and_ties(run_program):
    got = run_program(["80,80,79,100,12,80"]).lines[1:]
    assert got == ["Top 3: 100, 80, 80", "Lowest: 12", "80 or more: 4"], f"Got {got}"


def test_scores_list(run_program):
    scores = run_program(["5, 3,9"]).vars.get("scores")
    assert scores == [5, 3, 9], f"scores should be [5, 3, 9] in the order typed, got {scores!r}"
