from dojo_checks import run_pseudo


def test_other_item():
    _, variables = run_pseudo(
        replace={
            'item = "Notebook"': 'item = "Pen"',
            "price = 3": "price = 2",
            "quantity = 4": "quantity = 10",
        }
    )
    assert variables.get("line") == "Pen x10 = 20", (
        f"With a Pen at 2 x 10, line is {variables.get('line')!r}"
    )
