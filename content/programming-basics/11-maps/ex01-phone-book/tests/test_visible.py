def test_grace(run_program):
    assert run_program(["Grace"]).last_line == "Grace: 555-0199"
