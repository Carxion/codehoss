from dojo_checks import assert_fast


def test_edges():
    from main import binary_search

    assert binary_search([], 3) == -1
    assert binary_search([3], 3) == 0
    assert binary_search([1, 3], 3) == 1
    assert binary_search([1, 3], 4) == -1
    assert binary_search([1, 3], 0) == -1


def test_fast_on_a_million():
    from main import binary_search

    nums = list(range(0, 2_000_000, 2))
    queries = list(range(1_000_000, 2_000_000, 500))

    def run_all():
        return [binary_search(nums, q) for q in queries]

    result = assert_fast(
        run_all,
        budget=1.0,
        size="2,000 searches of 1,000,000 items",
        hint="Scanning is O(n) per search; halve the range each step for O(log n).",
    )
    assert result == [q // 2 if q % 2 == 0 else -1 for q in queries]
