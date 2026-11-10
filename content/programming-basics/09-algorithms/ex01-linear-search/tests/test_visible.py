import pytest


@pytest.fixture
def find(run_program):
    function = run_program().vars.get("find")
    assert callable(function), "Write a FUNCTION called find (check the spelling)."
    return function


def test_dog(find):
    assert find(["cat", "dog", "fox"], "dog") == 1
