def fib(n):
    # Correct but exponentially slow. Make it fast with memoisation.
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)
