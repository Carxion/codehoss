def contains_duplicate(nums):
    # This works, but compares every pair: O(n²). Make it O(n) with a set.
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] == nums[j]:
                return True
    return False
