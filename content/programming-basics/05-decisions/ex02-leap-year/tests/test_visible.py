def test_2024(run_program):
    assert run_program(["2024"]).last_line == "2024 is a leap year"


def test_2023(run_program):
    assert run_program(["2023"]).last_line == "2023 is not a leap year"
