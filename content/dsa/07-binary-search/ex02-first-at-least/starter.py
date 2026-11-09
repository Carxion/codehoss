def first_at_least(nums, target):
    # Correct but O(n). Use binary search for O(log n).
    for i, x in enumerate(nums):
        if x >= target:
            return i
    return len(nums)
