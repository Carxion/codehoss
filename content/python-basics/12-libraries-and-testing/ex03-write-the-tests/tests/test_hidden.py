import pytest

import main

RIGHT = main.is_valid_username


def _allowed(ch):
    return ch.islower() or ch.isdigit() or ch == "_"


def too_short_allowed(name):
    return 2 <= len(name) <= 15 and name[0].isalpha() and all(_allowed(c) for c in name)


def too_long_allowed(name):
    return 3 <= len(name) <= 16 and name[0].isalpha() and all(_allowed(c) for c in name)


def capitals_allowed(name):
    return 3 <= len(name) <= 15 and name[0].isalpha() and all(_allowed(c.lower()) for c in name)


def any_start_allowed(name):
    return 3 <= len(name) <= 15 and all(_allowed(c) for c in name)


def underscore_refused(name):
    return RIGHT(name) and "_" not in name


BROKEN = {
    "accepts 2-character names": too_short_allowed,
    "accepts 16-character names": too_long_allowed,
    "accepts capital letters": capitals_allowed,
    "accepts names starting with a digit or _": any_start_allowed,
    "refuses names with _": underscore_refused,
}


def _learner_tests():
    return [getattr(main, n) for n in dir(main) if n.startswith("test_")]


def _all_pass():
    for test in _learner_tests():
        try:
            test()
        except AssertionError:
            return False
    return True


def test_your_tests_pass_on_the_real_function():
    assert _learner_tests(), "Write some test_ functions"
    assert _all_pass(), "One of your tests fails on the correct function. Check what you expect."


@pytest.mark.parametrize("bug", list(BROKEN))
def test_your_tests_catch_a_broken_version(monkeypatch, bug):
    monkeypatch.setattr(main, "is_valid_username", BROKEN[bug])
    assert not _all_pass(), f"A broken version that {bug} passed all your tests. Add a test for it."
