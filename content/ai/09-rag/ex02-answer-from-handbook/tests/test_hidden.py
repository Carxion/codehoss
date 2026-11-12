import hoss_ai


def prompt_for(question, chunks, k=3):
    from main import answer

    hoss_ai.fake(chat=lambda messages, **kw: "ok")

    answer(question, chunks, k=k)
    return hoss_ai.calls[-1]["messages"][-1]["content"]


def test_prompt_layout():
    chunks = ["alpha beta", "gamma delta", "epsilon zeta"]
    got = prompt_for("alpha gamma", chunks, k=2)
    assert got.startswith("Context:\n") and got.endswith("\n\nQuestion: alpha gamma"), got
    assert got.count("\n\n") == 2, "Separate chunks with a blank line"


def test_retrieves_the_right_passage():
    from main import CHUNKS

    got = prompt_for("How much does express shipping cost?", CHUNKS)
    assert "Express shipping costs $49" in got, "The shipping passage should be in the context"
    context = got.split("\n\nQuestion:")[0].removeprefix("Context:\n")
    parts = context.split("\n\n")
    assert len(parts) == 3 and all(p in CHUNKS for p in parts), "Include exactly k=3 chunks"
