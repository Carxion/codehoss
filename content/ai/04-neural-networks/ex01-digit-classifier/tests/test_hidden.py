def test_model(run_program):
    v = run_program().vars
    assert v["model"].hidden_layer_sizes == (64,), "Use hidden_layer_sizes=(64,)"
    assert abs(v["accuracy"] - v["model"].score(v["X_test"], v["y_test"])) < 1e-9
