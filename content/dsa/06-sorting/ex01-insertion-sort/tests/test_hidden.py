from pathlib import Path


def no_builtin_sort():
    source = Path(__file__).with_name("main.py").read_text()
    assert "sorted(" not in source and ".sort(" not in source, (
        "Write the sort yourself: no sorted() or .sort()"
    )


def test_cases():
    from main import insertion_sort

    no_builtin_sort()
    original = [3, -1, 3, 0]
    assert insertion_sort(original) == [-1, 0, 3, 3]
    assert original == [3, -1, 3, 0], "Don't change the input list"
    assert insertion_sort([]) == [] and insertion_sort([1]) == [1]
