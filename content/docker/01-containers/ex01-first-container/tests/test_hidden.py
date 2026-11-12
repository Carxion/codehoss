from hoss_checks import inspect_container


def test_it_finished_cleanly():
    state = inspect_container("hello")["State"]
    assert state["Status"] == "exited" and state["ExitCode"] == 0
