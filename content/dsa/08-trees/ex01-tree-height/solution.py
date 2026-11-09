class Node:
    def __init__(self, value, left=None, right=None):
        self.value = value
        self.left = left
        self.right = right


def size(node):
    if node is None:
        return 0
    return 1 + size(node.left) + size(node.right)


def height(node):
    if node is None:
        return 0
    return 1 + max(height(node.left), height(node.right))
