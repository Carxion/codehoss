def most_frequent(items):
    counts = {}
    best, best_count = None, 0
    for x in items:
        counts[x] = counts.get(x, 0) + 1
        if counts[x] > best_count:
            best, best_count = x, counts[x]
    return best
