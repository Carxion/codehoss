from collections import deque


def shortest_hops(graph, start, goal):
    queue = deque([(start, 0)])
    visited = {start}
    while queue:
        node, dist = queue.popleft()
        if node == goal:
            return dist
        for nxt in graph.get(node, []):
            if nxt not in visited:
                visited.add(nxt)
                queue.append((nxt, dist + 1))
    return -1
