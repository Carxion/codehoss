def mean(*numbers):
    if len(numbers) == 0:
        return 0
    return sum(numbers) / len(numbers)


def summary(numbers, decimals=1):
    return min(numbers), max(numbers), round(mean(*numbers), decimals)


def add_score(score, scores=None):
    if scores is None:
        scores = []
    scores.append(score)
    return scores


print(mean(2, 4, 9))
print(summary([3, 8, 4]))
