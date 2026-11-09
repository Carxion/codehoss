"""End-to-end demo of the sandbox API.

    uv run dojo serve            # in one terminal
    uv run python scripts/api_demo.py
"""

import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"

with httpx.Client(base_url=BASE, timeout=60) as api:
    session = api.post("/sessions", json={"module_id": "python-basics"}).json()["session_id"]
    print(f"session {session[:8]} started")
    try:
        run = api.post(
            f"/sessions/{session}/run",
            json={"code": 'name = input("Name? ")\nprint(f"Hi {name}!")', "inputs": ["Ada"]},
        ).json()
        print(f"run      -> {run['stdout'].strip()!r} (exit {run['exit_code']})")

        escape = api.post(
            f"/sessions/{session}/run",
            json={"code": "import urllib.request\nurllib.request.urlopen('https://example.com')"},
        ).json()
        print(f"network  -> blocked: {escape['exit_code'] != 0}")

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
