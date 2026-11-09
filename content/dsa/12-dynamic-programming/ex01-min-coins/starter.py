def min_coins(coins, amount):
    # Greedy: always take the biggest coin that fits. Fast, but not always right!
    count = 0
    for c in sorted(coins, reverse=True):
        while amount >= c:
            amount -= c
            count += 1
    return count if amount == 0 else -1
