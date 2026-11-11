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


def test_length_edges():
    assert not is_valid_username("ab")
    assert is_valid_username("abc")
    assert is_valid_username("a" * 15)
    assert not is_valid_username("a" * 16)


def test_allowed_characters():
    assert is_valid_username("big_cat_7")
    assert not is_valid_username("BigCat")
    assert not is_valid_username("big-cat")


def test_must_start_with_a_letter():
    assert not is_valid_username("7cats")
    assert not is_valid_username("_cats")
