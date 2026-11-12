from hoss_checks import assert_fast


def test_unreachable_and_cycles():
    from main import shortest_hops

    graph = {"A": ["B"], "B": ["A"], "C": ["D"]}
    assert shortest_hops(graph, "A", "C") == -1
    assert shortest_hops(graph, "C", "D") == 1
    assert shortest_hops(graph, "D", "C") == -1


def test_prefers_short_route():
    from main import shortest_hops

    graph = {"S": ["L1", "G"], "L1": ["L2"], "L2": ["L3"], "L3": ["G"]}
    assert shortest_hops(graph, "S", "G") == 1


def test_wide_graph_is_fast():
    from main import shortest_hops

    n = 200_000
    graph = {"start": list(range(n)), n - 1: ["goal"]}
    result = assert_fast(
        shortest_hops,
        graph,
        "start",
        "goal",
        budget=1.0,
        size="200,000 neighbours",
        hint="list.pop(0) is O(n); use collections.deque and popleft().",
    )
    assert result == 2
