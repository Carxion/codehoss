def test_small():
    from main import BST

    tree = BST()
    for v in [50, 30, 70, 20, 40]:
        tree.insert(v)
    assert tree.contains(40) and not tree.contains(45)
    assert tree.in_order() == [20, 30, 40, 50, 70]
    assert tree.root.value == 50 and tree.root.left.value == 30
