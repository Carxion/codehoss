def average_of_evens(numbers):
    """The average of the even numbers (0 if there are none)."""
    total = 0
    count = 0
    for n in numbers:
        if n % 2 == 0:
            total += n
            count += 1
    if count == 0:
        return 0
    return total / count


def count_up_to(limit):
    """The numbers from 1 to limit, including limit."""
    return list(range(1, limit + 1))


def longest_word(words):
    """The longest word; if two tie, the first one wins."""
    best = ""
    for w in words:
        if len(w) > len(best):
            best = w
    return best


print(average_of_evens([1, 2, 3, 4]))
print(count_up_to(3))
print(longest_word(["hi", "hello", "hey"]))
