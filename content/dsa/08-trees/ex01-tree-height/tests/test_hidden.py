def test_empty_and_single():
    from main import Node, height, size

    assert size(None) == 0 and height(None) == 0
    assert size(Node(5)) == 1 and height(Node(5)) == 1


def test_lopsided():
    from main import Node, height, size

    root = None
    for v in range(10):
        root = Node(v, root)
    assert size(root) == 10
    assert height(root) == 10
    full = Node(4, Node(2, Node(1), Node(3)), Node(6, Node(5), Node(7)))
    assert size(full) == 7 and height(full) == 3
