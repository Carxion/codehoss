def test_square():
    from main import Square

    got = Square(3).describe()
    assert got == "square with area 9.00", f"Square(3).describe() gave {got!r}"
