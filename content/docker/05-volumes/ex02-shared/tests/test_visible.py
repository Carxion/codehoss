from dojo_checks import inspect_container


def test_writer_mounts_shared():
    info = inspect_container("writer")
    assert info["State"]["Running"], "writer should keep running"
    mounts = {m.get("Name"): m["Destination"] for m in info["Mounts"]}
    assert mounts.get("shared") == "/shared", f"mount the volume named shared at /shared (mounts: {mounts})"
