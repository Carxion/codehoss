"""The language server answers from inside its sandbox. Needs Docker + images."""

import queue

import pytest

from hoss.lsp import LanguageServer
from hoss.sandbox import docker_available, image_exists

pytestmark = [
    pytest.mark.docker,
    pytest.mark.skipif(
        not (docker_available() and image_exists("hoss-python")),
        reason="needs Docker and the hoss-python image (run `hoss build-images`)",
    ),
]

URI = "file:///work/main.py"


class Client:
    def __init__(self):
        self.inbox: queue.Queue[dict] = queue.Queue()
        self.server = LanguageServer("hoss-python", self.inbox.put)
        self.next_id = 0

    def request(self, method, params, timeout=60):
        self.next_id += 1
        self.server.send({"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params})
        while True:
            message = self.inbox.get(timeout=timeout)
            if message.get("id") == self.next_id and "method" not in message:
                return message.get("result")
            if message.get("method") == "workspace/configuration":
                items = message["params"]["items"]
                self.server.send(
                    {"jsonrpc": "2.0", "id": message["id"], "result": [{}] * len(items)}
                )

    def notify(self, method, params):
        self.server.send({"jsonrpc": "2.0", "method": method, "params": params})

    def wait_for(self, method, timeout=60):
        while True:
            message = self.inbox.get(timeout=timeout)
            if message.get("method") == method:
                return message["params"]


@pytest.fixture(scope="module")
def lsp():
    client = Client()
    client.request("initialize", {"processId": None, "rootUri": "file:///work", "capabilities": {}})
    client.notify("initialized", {})
    yield client
    client.server.close()
    assert not client.server.alive


def test_completes_library_members(lsp):
    lsp.notify(
        "textDocument/didOpen",
        {
            "textDocument": {
                "uri": URI,
                "languageId": "python",
                "version": 1,
                "text": "import math\nmath.",
            }
        },
    )
    result = lsp.request(
        "textDocument/completion",
        {"textDocument": {"uri": URI}, "position": {"line": 1, "character": 5}},
    )
    items = result["items"] if isinstance(result, dict) else result
    labels = {item["label"] for item in items}
    assert {"sqrt", "pi", "floor"} <= labels


def test_reports_undefined_names(lsp):
    lsp.notify(
        "textDocument/didChange",
        {"textDocument": {"uri": URI, "version": 2}, "contentChanges": [{"text": 'pirnt("hi")\n'}]},
    )
    # Diagnostics for the earlier `math.` text may still be in flight; wait for version 2.
    params = lsp.wait_for("textDocument/publishDiagnostics")
    while params.get("version") != 2:
        params = lsp.wait_for("textDocument/publishDiagnostics")
    assert any("pirnt" in d["message"] for d in params["diagnostics"]), params
