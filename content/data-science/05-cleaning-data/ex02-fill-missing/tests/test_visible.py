def test_no_missing_ages(run_program):
    clean = run_program().vars["clean"]
    assert clean["age"].isna().sum() == 0, "Fill the missing ages"
