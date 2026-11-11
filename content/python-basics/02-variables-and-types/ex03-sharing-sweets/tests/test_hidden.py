import re
from pathlib import Path

import pytest

MAIN = Path(__file__).with_name("main.py")


@pytest.mark.parametrize(("sweets", "children", "each", "left"), [(30, 4, 7, 2), (12, 3, 4, 0)])
def test_other_amounts(run_program, sweets, children, each, left):
    original = MAIN.read_text()
    changed = re.sub(r"^sweets = .*$", f"sweets = {sweets}", original, count=1, flags=re.M)
    changed = re.sub(r"^children = .*$", f"children = {children}", changed, count=1, flags=re.M)
    MAIN.write_text(changed)
    try:
        result = run_program()
    finally:
        MAIN.write_text(original)
    assert result.vars["each"] == each and result.vars["left_over"] == left, (
        f"With {sweets} sweets and {children} children, expected each={each} and "
        f"left_over={left}, got each={result.vars['each']} and left_over={result.vars['left_over']}. "
        "Calculate from the variables instead of typing the numbers."
    )
    assert result.lines == [f"Each child gets {each} sweets", f"Left over: {left}"]
