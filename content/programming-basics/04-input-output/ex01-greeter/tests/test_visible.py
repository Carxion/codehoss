def test_ada(run_program):
    got = run_program(["Ada", "36"]).last_line
    assert got == "Hello, Ada! Next year you will be 37.", f"Your program showed {got!r}"
