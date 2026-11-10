from dojo_checks import docker, inspect_container


def test_container_named_hello_exists():
    info = inspect_container("hello")
    assert info["Config"]["Image"] == "alpine:3.22", (
        f"hello was started from {info['Config']['Image']}; use alpine:3.22"
    )


def test_it_printed_the_message():
    logs = docker("logs", "hello")
    assert logs == "Hello from a container", f"hello printed {logs!r}"
