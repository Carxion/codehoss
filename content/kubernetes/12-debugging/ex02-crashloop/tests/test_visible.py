from hoss_checks import assert_rolled_out, kubectl


def test_worker_ready():
    assert_rolled_out("worker", timeout=60)
    assert "worker started in production mode" in kubectl("logs", "deploy/worker")
