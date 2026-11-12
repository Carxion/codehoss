from hoss_checks import assert_fast


def test_fast():
    from main import fib

    got = assert_fast(
        fib,
        90,
        budget=1.0,
        size="fib(90)",
        hint="Plain recursion recomputes the same values; memoise them.",
    )
    assert got == 2880067194370816120
