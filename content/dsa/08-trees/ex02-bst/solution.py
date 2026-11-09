class Node:
    def __init__(self, value, left=None, right=None):
        self.value = value
        self.left = left
        self.right = right


class BST:
    def __init__(self):
        self.root = None

    def insert(self, value):
        if self.root is None:
            self.root = Node(value)
            return
        node = self.root
        while True:
            if value == node.value:
                return
            side = "left" if value < node.value else "right"
            child = getattr(node, side)
            if child is None:
                setattr(node, side, Node(value))
                return
            node = child

    def contains(self, value):
        node = self.root
        while node is not None:
            if value == node.value:
                return True
            node = node.left if value < node.value else node.right
        return False

    def in_order(self):
        out = []

        def walk(node):
            if node is not None:
                walk(node.left)
                out.append(node.value)
                walk(node.right)

        walk(self.root)
        return out
