from dojo_checks import k8s, kubectl, wait_until


def test_log_served():
    k8s("pod", "shared")
    wait_until(
        lambda: k8s("pod", "shared")["status"]["phase"] == "Running",
        timeout=60,
        message="shared isn't running",
    )
    out = wait_until(
        lambda: _log(),
        timeout=30,
        message="web can't see log.txt: is the volume mounted at /shared in both containers?",
    )
    assert ":" in out, f"log.txt should hold times written by writer, got {out[:80]!r}"


def _log():
    try:
        return kubectl(
            "exec",
            "shared",
            "-c",
            "web",
            "--",
            "wget",
            "-qO-",
            "-T",
            "5",
            "http://127.0.0.1:8000/log.txt",
        )
    except AssertionError:
        return ""
