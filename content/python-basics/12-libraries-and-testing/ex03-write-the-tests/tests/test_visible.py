def test_your_tests_pass_on_the_real_function():
    import main

    tests = [getattr(main, n) for n in dir(main) if n.startswith("test_")]
    assert tests, "Write some test_ functions"
    for test in tests:
        test()
