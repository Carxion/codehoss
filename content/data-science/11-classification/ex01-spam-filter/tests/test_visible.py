def test_accuracy(run_program):
    accuracy = run_program().vars.get("accuracy")
    assert accuracy >= 0.9, f"accuracy is {accuracy:.2f}; aim for 0.9 or more"
