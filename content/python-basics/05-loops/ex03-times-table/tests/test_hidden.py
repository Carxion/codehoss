import pytest


@pytest.mark.parametrize("size", [1, 5, 10])
def test_sizes(run_program, size):
    expected = ["".join(f"{r * c:4}" for c in range(1, size + 1)) for r in range(1, size + 1)]
    got = run_program([str(size)]).lines[1:]
    assert got == expected, f"For size {size}, expected the rows {expected}, got {got}"
