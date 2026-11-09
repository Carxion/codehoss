def binary_search(nums, target):
    # Correct but O(n): checks every item. Make it O(log n).
    for i, x in enumerate(nums):
        if x == target:
            return i
    return -1
