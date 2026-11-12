from hoss_checks import inspect_container


def test_ticker_is_running():
    state = inspect_container("ticker")["State"]
    assert state["Running"], "ticker isn't running. Did you use -d, and does the loop keep going?"
