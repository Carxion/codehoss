def test_strong():
    from main import strength

    got = strength("Tr0ub4dor&3")
    assert got == "strong", f"strength('Tr0ub4dor&3') gave {got!r}"
