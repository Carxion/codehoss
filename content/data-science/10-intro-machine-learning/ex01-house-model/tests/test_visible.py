def test_model_trained(run_program):
    model = run_program().vars.get("model")
    assert hasattr(model, "coef_"), "Train model with .fit(...)"
