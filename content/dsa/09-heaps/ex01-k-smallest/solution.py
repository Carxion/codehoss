import heapq


def k_smallest(nums, k):
    h = list(nums)
    heapq.heapify(h)
    return [heapq.heappop(h) for _ in range(min(k, len(h)))]
