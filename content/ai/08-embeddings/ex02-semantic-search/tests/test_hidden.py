import dojo_ai


def test_ranking_and_k():
    from main import search

    docs = ["red apples", "green apples and pears", "blue cars"]
    assert search("apples pears", docs, k=2) == ["green apples and pears", "red apples"]
    assert len(search("apples", docs, k=3)) == 3


def test_one_embed_call():
    calls = []

    def counting_embed(texts):
        calls.append(texts)
        return [dojo_ai.simple_embed(t) for t in texts]

    from main import search

    dojo_ai.fake(embed=counting_embed)

    search("q", ["a", "b", "c"])
    assert len(calls) == 1, f"Embed everything in one call, not {len(calls)}"
