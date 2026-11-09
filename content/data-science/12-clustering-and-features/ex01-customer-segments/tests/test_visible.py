def test_segment_column(run_program):
    df = run_program().vars["df"]
    assert "segment" in df.columns, "Add a segment column"
    assert df["segment"].nunique() == 3, "There should be 3 segments"
