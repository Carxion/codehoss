import heapq


def cheapest_route(graph, start, goal):
    dist = {start: 0}
    previous = {}
    heap = [(0, start)]
    while heap:
        d, node = heapq.heappop(heap)
        if node == goal:
            break
        if d > dist[node]:
            continue
        for nxt, w in graph.get(node, []):
            nd = d + w
            if nxt not in dist or nd < dist[nxt]:
                dist[nxt] = nd
                previous[nxt] = node
                heapq.heappush(heap, (nd, nxt))
    if goal not in dist:
        return (None, [])
    path = [goal]
    while path[-1] != start:
        path.append(previous[path[-1]])
    path.reverse()
    return (dist[goal], path)
