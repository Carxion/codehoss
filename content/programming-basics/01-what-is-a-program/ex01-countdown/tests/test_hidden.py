def test_ends_with_lift_off(run_program):
    assert run_program().last_line == "Lift off!", "The last line should be exactly: Lift off!"
