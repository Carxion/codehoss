from dojo_checks import assert_fast


def test_edges():
    from main import count_islands

    assert count_islands([]) == 0
    assert count_islands(["...", "..."]) == 0
    assert count_islands(["#.#", ".#.", "#.#"]) == 5, "diagonals don't connect"
    assert count_islands(["###", "#.#", "###"]) == 1


def test_one_giant_island():
    from main import count_islands

    grid = ["#" * 400] * 400
    result = assert_fast(count_islands, grid, budget=3.0, size="a 400x400 map",
                         hint="Mark squares as seen when you push them so each is visited once.")
    assert result == 1
