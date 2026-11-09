def test_tip_rounding():
    from main import calculate_tip

    # 23.5 * 18% = 4.23 exactly; avoid half-cent cases, where float rounding surprises.
    assert calculate_tip(23.5, 18) == 4.23, (
        f"calculate_tip(23.5, 18) gave {calculate_tip(23.5, 18)}"
    )
    assert calculate_tip(19.99, 20) == 4.0, (
        f"calculate_tip(19.99, 20) gave {calculate_tip(19.99, 20)}"
    )
    assert calculate_tip(0, 20) == 0


def test_split():
    from main import split_bill

    assert split_bill(100, 3) == 33.33, f"split_bill(100, 3) gave {split_bill(100, 3)}"
    assert split_bill(60, 4) == 15.0
