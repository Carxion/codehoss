def test_accuracy(run_program):
    accuracy = run_program().vars.get("accuracy")
    assert accuracy >= 0.95, f"accuracy is {accuracy:.3f}"
