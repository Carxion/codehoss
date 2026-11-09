def test_sizes(run_program):
    v = run_program().vars
    assert v.get("segment_sizes") == sorted(v["df"]["segment"].value_counts().tolist())
    assert v["segment_sizes"] == [60, 60, 60], (
        f"segment_sizes is {v['segment_sizes']}; did you scale first?"
    )
