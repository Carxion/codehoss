def test_more():
    from main import redact

    assert redact("grace.hopper+bikes@navy.example.org") == "[EMAIL]"
    assert redact("Phone: 555.010.2222.") == "Phone: [PHONE]."
    assert redact("Order 1234 arrives in 5 days") == "Order 1234 arrives in 5 days", (
        "Short numbers aren't phones"
    )
    assert redact("no personal data here") == "no personal data here"
