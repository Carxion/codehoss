def test_types(run_program):
    v = run_program().vars
    assert type(v["price"]) is float, f"price should be a float, got {type(v['price']).__name__}"
    assert type(v["quantity"]) is int, (
        f"quantity should be an int, got {type(v['quantity']).__name__}"
    )


def test_total(run_program):
    total = run_program().vars["total"]
    assert total == 12.75, f"total should be 12.75, got {total!r}"
