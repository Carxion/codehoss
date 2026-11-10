from dojo_checks import inspect_container


def test_restart_policy():
    policy = inspect_container("flaky")["HostConfig"]["RestartPolicy"]
    assert policy["Name"] == "on-failure", f"the policy is {policy['Name']!r}; use --restart on-failure:3"
    assert policy["MaximumRetryCount"] == 3, "limit it to 3 restarts: on-failure:3"
