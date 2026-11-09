import random


def test_roll_dice_uses_rng():
    from main import roll_dice

    expected_rng = random.Random(7)
    expected = [expected_rng.randint(1, 6) for _ in range(20)]
    rolls = roll_dice(20, random.Random(7))
    assert rolls == expected, "Use rng.randint(1, 6) for every roll"
    assert all(1 <= r <= 6 for r in rolls)


def test_roll_count():
    from main import roll_dice

    assert len(roll_dice(0, random.Random(1))) == 0
    assert len(roll_dice(50, random.Random(1))) == 50
