from dojo_checks import assert_fast


def test_unreachable_left_out():
    from main import distances

    graph = {"A": [("B", 1)], "B": [], "C": [("A", 1)]}
    assert distances(graph, "A") == {"A": 0, "B": 1}


def test_cheap_detour_beats_direct():
    from main import distances

    graph = {"S": [("G", 10), ("X", 1)], "X": [("Y", 1)], "Y": [("G", 1)]}
    assert distances(graph, "S")["G"] == 3


def test_grid_is_fast():
    from main import distances

    n = 100
    graph = {}
    for r in range(n):
        for c in range(n):
            edges = []
            for nr, nc in ((r + 1, c), (r, c + 1), (r - 1, c), (r, c - 1)):
                if 0 <= nr < n and 0 <= nc < n:
                    edges.append(((nr, nc), 1 if nr == r else 2))
            graph[(r, c)] = edges
    dist = assert_fast(
        distances,
        graph,
        (0, 0),
        budget=2.0,
        size="a 10,000-node grid",
        hint="Pop the next closest node from a heap instead of scanning them all.",
    )
    assert len(dist) == n * n
    assert dist[(n - 1, n - 1)] == (n - 1) * 1 + (n - 1) * 2
