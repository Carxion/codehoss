def test_reasonable(run_program):
    predicted = float(run_program().vars.get("predicted"))
    assert 200_000 < predicted < 600_000, f"predicted is {predicted:,.0f}; is the model trained?"
