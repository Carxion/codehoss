from pathlib import Path


def test_all_three_lines(run_program):
    got = run_program().lines
    expected = ["Seconds in an hour: 3600", "Minutes in a day: 1440", "Hours in a week: 168"]
    assert got == expected, f"Expected the lines {expected}, got {got}"


def test_python_does_the_maths():
    source = Path(__file__).with_name("main.py").read_text()
    for answer in ("3600", "1440", "168"):
        assert answer not in source, (
            f"Write the sum that makes {answer} (like 60 * 60), not the number itself"
        )
