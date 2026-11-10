import json

from dojo_checks import sh


def history():
    proc = sh("helm history blog -o json")
    assert proc.returncode == 0, "no release called blog yet: helm install blog ./chart"
    return json.loads(proc.stdout)


def test_rolled_back_to_2():
    revisions = history()
    assert len(revisions) == 4, (
        f"blog has {len(revisions)} revision(s); install, two upgrades and a rollback make 4"
    )
    assert revisions[-1]["description"] == "Rollback to 2", (
        f"the last revision says {revisions[-1]['description']!r}"
    )
