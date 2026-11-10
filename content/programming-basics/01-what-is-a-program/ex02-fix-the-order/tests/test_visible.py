def test_first_step(run_program):
    assert run_program().lines[0] == "1. Boil the water", "Start by boiling the water"
