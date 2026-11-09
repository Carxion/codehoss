def test_card_has_three_lines(run_program):
    lines = run_program().lines
    assert len(lines) == 3, f"The card should be 3 lines tall, but you printed {len(lines)}"
