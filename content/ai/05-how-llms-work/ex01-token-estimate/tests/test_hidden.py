def test_edge_cases():
    from main import cost, rough_tokens

    assert rough_tokens("") == 0
    assert rough_tokens("a b c d e f") == 8
    assert abs(cost("word " * 1000, 3.0) - 1334 * 3.0 / 1_000_000) < 1e-12
