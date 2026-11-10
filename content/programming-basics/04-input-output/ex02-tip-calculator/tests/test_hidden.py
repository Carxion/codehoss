def test_with_cents(run_program):
    lines = run_program(["25.50", "20"]).lines
    assert lines[-2:] == ["Tip: 5.1", "Total: 30.6"], (
        f"For 25.50 at 20% the last two lines were {lines[-2:]}"
    )


def test_rounding(run_program):
    lines = run_program(["10", "12.5"]).lines
    assert lines[-2:] == ["Tip: 1.25", "Total: 11.25"]
