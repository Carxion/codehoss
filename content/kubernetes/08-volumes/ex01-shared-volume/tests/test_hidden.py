from dojo_checks import k8s


def test_emptydir_in_both():
    spec = k8s("pod", "shared")["spec"]
    volumes = {v["name"]: v for v in spec.get("volumes", [])}
    assert "emptyDir" in volumes.get("shared", {}), "add a volume named shared with emptyDir: {}"
    for c in spec["containers"]:
        mounts = {m["name"]: m["mountPath"] for m in c.get("volumeMounts", [])}
        assert mounts.get("shared") == "/shared", f"mount shared at /shared in {c['name']}"
