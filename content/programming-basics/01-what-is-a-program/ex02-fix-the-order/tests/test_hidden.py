EXPECTED = [
    "1. Boil the water",
    "2. Put a tea bag in the cup",
    "3. Pour the water into the cup",
    "4. Wait 3 minutes",
    "5. Take out the tea bag",
]


def test_all_in_order(run_program):
    lines = run_program().lines
    assert sorted(lines) == sorted(EXPECTED), (
        "Keep all five lines exactly as they were; only move them"
    )
    assert lines == EXPECTED, f"The order is still {[line[0] for line in lines]}"
