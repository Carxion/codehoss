def test_small_tree():
    from main import Node, height, size

    root = Node(2, Node(1), Node(3, None, Node(4)))
    assert size(root) == 4
    assert height(root) == 3
