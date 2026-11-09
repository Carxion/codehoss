from dojo.grader import run_snippet, run_tests

TEST = """
def test_greets(run_program):
    assert run_program(["Ada"]).last_line == "Hi Ada", "should greet by name"
"""


def _write_test(tmp_path, text=TEST):
    path = tmp_path / "test_hidden.py"
    path.write_text(text, encoding="utf-8")
    return path


def test_passing_code(tmp_path):
    result = run_tests(
        'name = input("Name? ")\nprint("Hi", name)\n', [_write_test(tmp_path)], timeout=5
    )
    assert result.passed
    assert [r.outcome for r in result.results] == ["passed"]


def test_failing_code_reports_assert_message(tmp_path):
    result = run_tests('input()\nprint("Hello")\n', [_write_test(tmp_path)], timeout=5)
    assert not result.passed
    assert result.results[0].message == "should greet by name"


def test_learner_exception_is_a_failure(tmp_path):
    result = run_tests("pirnt('x')\n", [_write_test(tmp_path)], timeout=5)
    assert not result.passed
    assert "NameError" in result.results[0].message


def test_asking_for_too_much_input_fails(tmp_path):
    result = run_tests("input()\ninput()\n", [_write_test(tmp_path)], timeout=5)
    assert "more input" in result.results[0].message


def test_infinite_loop_times_out(tmp_path):
    result = run_tests("while True:\n    pass\n", [_write_test(tmp_path)], timeout=0.5)
    assert result.timed_out
    assert not result.passed


def test_snippet_sees_output_and_variables():
    assert run_snippet("x = 2\nprint('hi')", "assert x == 2 and _output == 'hi\\n'").passed


def test_snippet_failure_message():
    result = run_snippet("x = 1", "assert x == 2, 'x should be 2'")
    assert not result.passed
    assert result.message == "x should be 2"
