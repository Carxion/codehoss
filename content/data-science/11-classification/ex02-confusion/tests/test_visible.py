def test_shape(run_program):
    cm = run_program().vars.get("cm")
    assert cm is not None and cm.shape == (2, 2), "cm should be a 2x2 confusion matrix"
