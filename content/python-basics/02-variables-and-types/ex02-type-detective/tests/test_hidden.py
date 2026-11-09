def test_born_is_int(run_program):
    born = run_program().vars.get("born")
    assert type(born) is int and born == 1815, f"born should be the whole number 1815, got {born!r}"


def test_height_is_float(run_program):
    height = run_program().vars.get("height_m")
    assert type(height) is float and height == 1.65, f"height_m should be 1.65, got {height!r}"


def test_is_programmer_is_bool(run_program):
    value = run_program().vars.get("is_programmer")
    assert value is True, f"is_programmer should be True (no quotes), got {value!r}"
