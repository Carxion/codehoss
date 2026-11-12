import json

from hoss_checks import sh


def compose_services():
    proc = sh("docker compose ps --format json")
    assert proc.returncode == 0, proc.stderr
    lines = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    return {c["Service"]: c for c in lines}


def test_two_services_running():
    services = compose_services()
    assert set(services) >= {"api", "web"}, f"running services: {sorted(services)}"
    assert all(s["State"] == "running" for s in services.values())


def test_api_not_published():
    api = compose_services()["api"]
    published = [p for p in api.get("Publishers") or [] if p.get("PublishedPort")]
    assert not published, "don't publish the API's port: web reaches it over the Compose network"
