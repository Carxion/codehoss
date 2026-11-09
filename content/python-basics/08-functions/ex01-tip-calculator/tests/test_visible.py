def test_tip():
    from main import calculate_tip

    assert calculate_tip(50, 20) == 10.0, f"calculate_tip(50, 20) gave {calculate_tip(50, 20)}"
