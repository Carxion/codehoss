"""Copied into grading runs as dojo_checks.py: friendly assertions for data exercises.

Exercise tests import these instead of writing raw comparisons, so failures read like
advice ("column 'total' is missing") rather than a pandas stack trace.
"""

import math
import signal
import time


def assert_close(actual, expected, *, name="value", tol=1e-6):
    assert isinstance(actual, int | float) and not isinstance(actual, bool), (
        f"{name} should be a number, but it is {type(actual).__name__}"
    )
    assert math.isclose(actual, expected, rel_tol=tol, abs_tol=tol), (
        f"{name} should be {expected}, but it is {actual}"
    )


def assert_frame_matches(actual, expected, *, name="df", sort_by=None, tol=1e-6):
    import pandas as pd

    assert isinstance(actual, pd.DataFrame), (
        f"{name} should be a DataFrame, but it is {type(actual).__name__}"
    )
    missing = [c for c in expected.columns if c not in actual.columns]
    extra = [c for c in actual.columns if c not in expected.columns]
    assert not missing, f"{name} is missing column(s): {', '.join(map(str, missing))}"
    assert not extra, f"{name} has unexpected column(s): {', '.join(map(str, extra))}"
    assert len(actual) == len(expected), (
        f"{name} should have {len(expected)} rows, but it has {len(actual)}"
    )
    actual = actual[list(expected.columns)]
    if sort_by:
        actual = actual.sort_values(sort_by)
        expected = expected.sort_values(sort_by)
    actual = actual.reset_index(drop=True)
    expected = expected.reset_index(drop=True)
    for column in expected.columns:
        for row, (a, e) in enumerate(zip(actual[column], expected[column], strict=True)):
            if not _same(a, e, tol):
                raise AssertionError(
                    f"{name}: row {row}, column '{column}' is {a!r}, expected {e!r}"
                )


def assert_series_matches(actual, expected, *, name="series", tol=1e-6):
    import pandas as pd

    assert isinstance(actual, pd.Series), (
        f"{name} should be a Series, but it is {type(actual).__name__}"
    )
    assert list(actual.index) == list(expected.index), (
        f"{name} should have index {list(expected.index)}, but it has {list(actual.index)}"
    )
    for label, a, e in zip(expected.index, actual, expected, strict=True):
        if not _same(a, e, tol):
            raise AssertionError(f"{name}[{label!r}] is {a!r}, expected {e!r}")


def figures():
    """Describe every open matplotlib figure: titles, labels and what was drawn."""
    import matplotlib.pyplot as plt

    described = []
    for number in plt.get_fignums():
        figure = plt.figure(number)
        axes = []
        for ax in figure.axes:
            legend = ax.get_legend()
            axes.append(
                {
                    "title": ax.get_title(),
                    "xlabel": ax.get_xlabel(),
                    "ylabel": ax.get_ylabel(),
                    "lines": len(ax.lines),
                    "bars": len(ax.patches),
                    "scatter": sum(1 for c in ax.collections if c.get_offsets().size),
                    "legend": [t.get_text() for t in legend.get_texts()] if legend else [],
                }
            )
        described.append({"axes": axes})
    return described


def first_axes():
    found = figures()
    assert found and found[0]["axes"], "No chart was drawn. Did you call a plotting function?"
    return found[0]["axes"][0]


def _same(a, e, tol):
    if isinstance(e, float) or isinstance(a, float):
        try:
            if math.isnan(e) and math.isnan(a):
                return True
            return math.isclose(float(a), float(e), rel_tol=tol, abs_tol=tol)
        except (TypeError, ValueError):
            return False
    return a == e


class _TooSlow(Exception):
    pass


def assert_fast(fn, *args, budget=1.0, size="this input", hint="", **kwargs):
    """Run fn(*args) and fail with advice if it takes longer than `budget` seconds.

    In the sandbox a timer interrupts slow code, so an O(n**2) attempt fails in about
    `budget` seconds instead of running for minutes. Returns fn's result.
    """
    message = f"Too slow: over {budget:g}s on {size}."
    if hint:
        message += f" {hint}"
    can_interrupt = hasattr(signal, "setitimer")
    if can_interrupt:

        def _alarm(signum, frame):
            raise _TooSlow

        previous = signal.signal(signal.SIGALRM, _alarm)
        signal.setitimer(signal.ITIMER_REAL, budget)
    started = time.perf_counter()
    try:
        result = fn(*args, **kwargs)
    except _TooSlow:
        raise AssertionError(message) from None
    finally:
        if can_interrupt:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous)
    if time.perf_counter() - started > budget:
        raise AssertionError(message)
    return result


# --- labs ---------------------------------------------------------------------------
# Lab checks look at real state: files in the exercise folder, the lab's Docker
# engine, and web apps the learner started. Failures should say what to do next.


def lab_dir():
    import os
    from pathlib import Path

    return Path(os.environ.get("LAB_DIR", "."))


def lab_file(name):
    """Text of a file in the exercise folder, failing helpfully if it's missing."""
    path = lab_dir() / name
    assert path.is_file(), f"There's no {name} in {lab_dir()} yet. Create it in the editor."
    return path.read_text()


def sh(command, *, timeout=60, check=False):
    """Run a shell command in the exercise folder; returns the CompletedProcess."""
    import subprocess

    proc = subprocess.run(
        command, shell=True, cwd=lab_dir(), capture_output=True, text=True, timeout=timeout
    )
    if check:
        assert proc.returncode == 0, f"`{command}` failed:\n{(proc.stderr or proc.stdout).strip()}"
    return proc


def docker(*args, timeout=60):
    """Run a docker command against the lab engine; returns its stdout (stripped).
    Raises AssertionError with docker's message if it fails."""
    import shlex

    proc = sh("docker " + " ".join(shlex.quote(str(a)) for a in args), timeout=timeout)
    assert proc.returncode == 0, (proc.stderr or proc.stdout).strip()
    return proc.stdout.strip()


def image_exists(name):
    return sh(f"docker image inspect {name}").returncode == 0


def assert_image(name):
    """The image exists, or fail with the build command to try."""
    assert image_exists(name), (
        f"No image called {name} yet. Build it in the terminal: docker build -t {name} ."
    )
    import json

    return json.loads(docker("image", "inspect", name))[0]


def containers(*filters, all=False):
    """Container info dicts (docker ps --format json), optionally filtered."""
    import json

    args = ["ps", "--no-trunc", "--format", "{{json .}}"]
    if all:
        args.append("--all")
    for f in filters:
        args += ["--filter", f]
    return [json.loads(line) for line in docker(*args).splitlines() if line]


def inspect_container(name):
    import json

    proc = sh(f"docker container inspect {name}")
    assert proc.returncode == 0, (
        f"There's no container called {name}. Did you start it with --name {name}?"
    )
    return json.loads(proc.stdout)[0]


def http_get(url, *, timeout=10, wait=0):
    """GET a URL and return (status, body). Retries for up to `wait` seconds while
    the app is starting. Apps published with -p are on the lab engine: http://docker:PORT."""
    import time
    import urllib.error
    import urllib.request

    deadline = time.monotonic() + wait
    while True:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return response.status, response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", errors="replace")
        except OSError as e:
            if time.monotonic() >= deadline:
                raise AssertionError(
                    f"Nothing answered at {url} ({e}). Is the container running, "
                    "with its port published (-p HOST:CONTAINER)?"
                ) from None
            time.sleep(0.5)
