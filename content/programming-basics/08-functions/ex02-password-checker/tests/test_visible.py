import pytest


@pytest.fixture
def strong(run_program):
    function = run_program().vars.get("strong")
    assert callable(function), "Write a FUNCTION called strong (check the spelling)."
    return function


def test_examples(strong):
    assert strong("sunshine7") is True, 'strong("sunshine7") should be TRUE'
    assert strong("sunshine") is False, 'strong("sunshine") has no digit, so FALSE'
