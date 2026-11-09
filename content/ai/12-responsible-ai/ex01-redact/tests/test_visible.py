def test_example():
    from main import redact

    assert (
        redact("Call +1 (555) 010-9999 or mail ada@lumen.example") == "Call [PHONE] or mail [EMAIL]"
    )
