from dojo_checks import run_pseudo


def test_other_numbers():
    _, variables = run_pseudo(replace={"a = 7": "a = 1", "b = 8": "b = 2", "c = 10": "c = 2"})
    assert variables.get("average") == 1.7, (
        f"The average of 1, 2 and 2 is 1.7, got {variables.get('average')}"
    )


def test_whole_number():
    out, _ = run_pseudo(replace={"a = 7": "a = 3", "b = 8": "b = 3", "c = 10": "c = 3"})
    assert out.strip() == "Average: 3"
