def test_three_students(run_program):
    lines = run_program(["3", "Ada", "95", "Grace", "72", "Alan", "58"]).lines
    assert lines[-5:] == [
        "Ada: A",
        "Grace: C",
        "Alan: F",
        "Class average: 75",
        "Top student: Ada",
    ], f"The end of the output was {lines[-5:]}"
