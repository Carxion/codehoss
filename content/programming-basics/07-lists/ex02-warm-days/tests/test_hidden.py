from dojo_checks import run_pseudo


def test_other_week():
    out, variables = run_pseudo(
        replace={"temperatures = [18, 22, 19, 25, 21, 20]": "temperatures = [30, 10, 21, 20, 28]"}
    )
    assert variables.get("warm_days") == [30, 21, 28], "20 is not above 20, so it stays out"
    assert out.strip().splitlines()[-1] == "3 warm days: [30, 21, 28]"


def test_cold_week():
    out, _ = run_pseudo(
        replace={"temperatures = [18, 22, 19, 25, 21, 20]": "temperatures = [5, 8]"}
    )
    assert out.strip().splitlines()[-1] == "0 warm days: []"
