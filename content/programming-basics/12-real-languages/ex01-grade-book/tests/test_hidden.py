def test_grade_function(run_program):
    grade = run_program(["1", "X", "50"]).vars.get("grade")
    assert callable(grade), "Keep the FUNCTION called grade"
    assert [grade(s) for s in (100, 90, 89, 80, 79, 70, 69, 60, 59, 0)] == list("AABBCCDDFF")


def test_four_students(run_program):
    lines = run_program(["4", "Lin", "81", "Sam", "99", "Kai", "64", "Ola", "99"]).lines
    assert lines[-6:] == [
        "Lin: B",
        "Sam: A",
        "Kai: D",
        "Ola: A",
        "Class average: 85.8",
        "Top student: Sam",
    ], f"The end of the output was {lines[-6:]}. On a tie the first student entered is top."
