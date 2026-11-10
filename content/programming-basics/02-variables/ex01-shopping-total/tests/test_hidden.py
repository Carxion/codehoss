from dojo_checks import run_pseudo


def test_other_values():
    out, variables = run_pseudo(replace={"price = 4": "price = 7", "quantity = 3": "quantity = 5"})
    assert variables.get("total") == 35, (
        "With price 7 and quantity 5, total should be 35. Use the variables, not the numbers."
    )
    assert out.strip().splitlines()[-1] == "Total: 35"
