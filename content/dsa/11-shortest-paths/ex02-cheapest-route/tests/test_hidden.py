def test_edges():
    from main import cheapest_route

    graph = {"A": [("B", 2)], "B": [("C", 2)], "C": []}
    assert cheapest_route(graph, "A", "A") == (0, ["A"])
    assert cheapest_route(graph, "C", "A") == (None, [])
    assert cheapest_route(graph, "A", "C") == (4, ["A", "B", "C"])


def test_detour():
    from main import cheapest_route

    graph = {"S": [("G", 10), ("X", 1)], "X": [("Y", 1)], "Y": [("G", 1)]}
    assert cheapest_route(graph, "S", "G") == (3, ["S", "X", "Y", "G"])
