"""End-to-end demo of the API without the browser.

uv run dojo serve            # in one terminal
uv run python scripts/api_demo.py
"""

import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
DEMO_USER = {"username": "api-demo", "password": "api-demo-password"}

with httpx.Client(base_url=f"{BASE}/api", timeout=60) as api:
    if api.post("/auth/login", json=DEMO_USER).status_code != 200:
        api.post("/auth/register", json=DEMO_USER).raise_for_status()
    session = api.post("/sessions", json={"module_id": "python-basics"}).json()["session_id"]
    print(f"session {session[:8]} started")
    try:
        run = api.post(
            f"/sessions/{session}/run",
            json={"code": 'name = input("Name? ")\nprint(f"Hi {name}!")', "inputs": ["Ada"]},
        ).json()
        print(f"run      -> {run['stdout'].strip()!r} (exit {run['exit_code']})")

        oops = api.post(f"/sessions/{session}/run", json={"code": 'pirnt("hi")'}).json()
        print(f"error    -> {oops['explanation']['message']}")

        for label, code in [
            ("starter ", "# Write your code below this line.\n"),
            ("solution", 'print("Hello, world!")\nprint("I am learning Python.")\n'),
        ]:
            check = api.post(
                f"/sessions/{session}/check", json={"exercise_id": "py.hello", "code": code}
            ).json()
            summary = ", ".join(f"{r['label']}={r['outcome']}" for r in check["results"])
            print(f"check {label} -> passed={check['passed']} ({summary})")
    finally:
        api.delete(f"/sessions/{session}")
        print("session closed")
