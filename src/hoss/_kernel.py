"""Notebook kernel: runs inside a sandbox, spoken to over stdin/stdout as JSON lines.

Started with `python -u -c <this source>` via `docker exec -i`, so it needs no files in
the image. Uses IPython's InteractiveShell for real notebook behaviour (last expression
displayed, rich reprs such as DataFrame tables, inline matplotlib charts).

In:  {"id": <n>, "code": "..."}            one line per cell to run
Out: {"type": "ready", "pid": <pid>}
     {"id", "type": "stream", "name": "stdout" | "stderr", "text"}
     {"id", "type": "display" | "result", "data": {mime: value}}
     {"id", "type": "error", "ename", "evalue", "traceback"}
     {"id", "type": "done", "status": "ok" | "error", "execution_count"}
"""

import collections
import itertools
import json
import os
import signal
import sys

# `docker exec` starts us with SIGINT ignored, which would make Interrupt do nothing.
signal.signal(signal.SIGINT, signal.default_int_handler)

# Keep the real stdout for the protocol; anything else that writes to fd 1 (like a
# subprocess) goes to stderr instead, so it can't corrupt the message stream.
_protocol = os.fdopen(os.dup(1), "w", encoding="utf-8")
os.dup2(2, 1)

MAX_TEXT = 100_000
KEEP_MIME = ("text/plain", "text/html", "text/markdown", "image/png", "image/svg+xml")
current_id = None


def send(message):
    _protocol.write(json.dumps(message) + "\n")
    _protocol.flush()


def clean(data):
    out = {}
    for mime in KEEP_MIME:
        if mime in data:
            value = data[mime]
            if isinstance(value, str) and len(value) > MAX_TEXT:
                value = value[:MAX_TEXT] + "\n… (output truncated)"
            out[mime] = value
    return out


class StreamWriter:
    encoding = "utf-8"

    def __init__(self, name):
        self.name = name

    def write(self, text):
        if text:
            send({"id": current_id, "type": "stream", "name": self.name, "text": text[:MAX_TEXT]})
        return len(text)

    def flush(self):
        pass

    def isatty(self):
        return False


class NoInput:
    def readline(self, *args):
        raise RuntimeError(
            "Notebooks can't read keyboard input. Put the value in a variable instead."
        )

    read = readline


sys.stdout = StreamWriter("stdout")
sys.stderr = StreamWriter("stderr")

from IPython.core.displayhook import DisplayHook  # noqa: E402
from IPython.core.displaypub import DisplayPublisher  # noqa: E402
from IPython.core.interactiveshell import InteractiveShell  # noqa: E402


class Publisher(DisplayPublisher):
    def publish(self, data, metadata=None, source=None, *, transient=None, update=False, **kw):
        send({"id": current_id, "type": "display", "data": clean(data)})

    def clear_output(self, wait=False):
        pass


class ResultHook(DisplayHook):
    def write_output_prompt(self):
        pass

    def write_format_data(self, format_dict, md_dict=None):
        send({"id": current_id, "type": "result", "data": clean(format_dict)})

    def finish_displayhook(self):
        pass


shell = InteractiveShell.instance(displayhook_class=ResultHook, display_pub_class=Publisher)
try:
    shell.colors = "nocolor"
except Exception:  # noqa: BLE001 - older IPython spells it differently
    shell.colors = "NoColor"


def show_traceback(etype, evalue, stb):
    send(
        {
            "id": current_id,
            "type": "error",
            "ename": etype.__name__,
            "evalue": str(evalue),
            "traceback": shell.InteractiveTB.stb2text(stb),
        }
    )


shell._showtraceback = show_traceback

try:
    shell.enable_matplotlib("inline")
except Exception:  # noqa: BLE001 - matplotlib is optional
    pass
try:
    import pandas as pd

    pd.set_option("display.max_rows", 30)
    pd.set_option("display.max_columns", 20)
except ImportError:
    pass

sys.stdin = NoInput()
send({"type": "ready", "pid": os.getpid()})

_requests = os.fdopen(0, "r", encoding="utf-8")
_pending = collections.deque()  # cells queued while a cell waited for an AI reply
_ai_requests = itertools.count(1)


def _ai_transport(kind, payload):
    """hoss_ai -> the CodeHoss server, which calls the learner's chosen model.

    The sandbox has no network: the request goes out on the protocol channel and the
    reply comes back on stdin, interleaved with any cells queued in the meantime.
    """
    req = next(_ai_requests)
    send({"id": current_id, "type": "ai_request", "req": req, "kind": kind, "payload": payload})
    while True:
        line = _requests.readline()
        if not line:
            raise RuntimeError("The connection to CodeHoss closed.")
        message = json.loads(line)
        if message.get("ai_reply") == req:
            return message
        if "code" in message:
            _pending.append(message)
        # Anything else is a late reply to an interrupted request; drop it.


try:
    import hoss_ai

    hoss_ai._transport = _ai_transport
except ImportError:
    pass

while True:
    if _pending:
        request = _pending.popleft()
    else:
        try:
            line = _requests.readline()
        except KeyboardInterrupt:
            continue  # an interrupt arrived between cells
        if not line:
            break
        request = json.loads(line)
        if "code" not in request:
            continue  # a late AI reply after an interrupt
    current_id = request["id"]
    try:
        result = shell.run_cell(request["code"], store_history=True)
        ok = result.success
    except KeyboardInterrupt:
        send(
            {
                "id": current_id,
                "type": "error",
                "ename": "KeyboardInterrupt",
                "evalue": "",
                "traceback": "",
            }
        )
        ok = False
    send(
        {
            "id": current_id,
            "type": "done",
            "status": "ok" if ok else "error",
            "execution_count": shell.execution_count - 1,
        }
    )
