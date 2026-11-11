def is_valid_username(name):
    """3-15 characters; lowercase letters, digits and _; starts with a letter."""
    if not 3 <= len(name) <= 15:
        return False
    if not name[0].isalpha():
        return False
    for ch in name:
        if not (ch.islower() or ch.isdigit() or ch == "_"):
            return False
    return True


def test_a_normal_name():
    assert is_valid_username("ana_99")


# TODO: write more tests: one for each rule, including the edges.
