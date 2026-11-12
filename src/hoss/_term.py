"""Terminal bridge, run inside a lab session: `python -c <this> <start dir>`.

`docker exec` without -t has no terminal, so this gives bash a real pseudo-terminal
(colours, line editing, Ctrl-C, full-screen programs). stdin carries JSON lines:
{"i": "keys"} is typed input and {"r": [cols, rows]} resizes. stdout is the raw
terminal output, passed straight to xterm.js in the browser.
"""

import fcntl
import json
import os
import pty
import select
import struct
import sys
import termios

start = sys.argv[1] if len(sys.argv) > 1 else "/work"
pid, fd = pty.fork()
if pid == 0:
    os.chdir(start if os.path.isdir(start) else "/work")
    os.environ.update(
        TERM="xterm-256color", PS1=r"\[\e[1;32m\]learner\[\e[0m\]:\[\e[1;34m\]\w\[\e[0m\]$ "
    )
    os.execvp("bash", ["bash", "--norc", "--noprofile", "-i"])

STDIN, STDOUT = 0, 1
pending = b""
while True:
    try:
        readable, _, _ = select.select([fd, STDIN], [], [])
    except InterruptedError:
        continue
    if fd in readable:
        try:
            data = os.read(fd, 65536)
        except OSError:
            break  # bash exited
        if not data:
            break
        while data:
            data = data[os.write(STDOUT, data) :]
    if STDIN in readable:
        chunk = os.read(STDIN, 65536)
        if not chunk:
            break  # the browser went away
        pending += chunk
        *lines, pending = pending.split(b"\n")
        for line in lines:
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if "i" in message:
                os.write(fd, str(message["i"]).encode("utf-8"))
            elif "r" in message:
                cols, rows = (max(2, min(int(v), 500)) for v in message["r"])
                fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))

try:
    os.kill(pid, 9)
except OSError:
    pass
