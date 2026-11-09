import pytest

from dojo.store import AuthError, Store


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "dojo.db")


def test_register_login_and_tokens(store):
    user = store.register("Ada", "correct horse")
    assert user.username == "ada"
    assert store.authenticate("ADA", "correct horse").id == user.id
    token = store.create_token(user)
    assert store.user_for_token(token).id == user.id
    store.revoke_token(token)
    assert store.user_for_token(token) is None


@pytest.mark.parametrize(
    ("username", "password", "message"),
    [("ab", "longenough", "3-32"), ("bad name", "longenough", "3-32"), ("okname", "short", "8")],
)
def test_registration_rules(store, username, password, message):
    with pytest.raises(AuthError, match=message):
        store.register(username, password)


def test_duplicate_username(store):
    store.register("ada", "password1")
    with pytest.raises(AuthError, match="taken"):
        store.register("ADA", "password2")


def test_wrong_password(store):
    store.register("ada", "password1")
    with pytest.raises(AuthError):
        store.authenticate("ada", "password2")


def test_progress_merges_and_never_undoes(store):
    user = store.register("ada", "password1")
    store.record(user, "m", "l/1", attempt=True)
    store.record(user, "m", "l/1", attempt=True, hints_used=2)
    store.record(user, "m", "l/1", attempt=True, done=True)
    store.record(user, "m", "l/1", attempt=True, done=False, hints_used=1)
    p = store.progress(user, "m")["l/1"]
    assert (p.done, p.attempts, p.hints_used, p.showed_solution) == (True, 4, 2, False)
