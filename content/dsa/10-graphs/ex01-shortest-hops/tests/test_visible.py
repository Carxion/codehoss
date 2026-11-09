GRAPH = {"A": ["B", "C"], "B": ["A", "D"], "C": ["A", "D"], "D": ["B", "C", "E"], "E": ["D"]}


def test_hops():
    from main import shortest_hops

    assert shortest_hops(GRAPH, "A", "E") == 3
    assert shortest_hops(GRAPH, "A", "A") == 0
