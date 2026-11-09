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
