import dojo_ai


def test_history_and_system():
    from main import Chatbot

    dojo_ai.fake(chat=lambda messages, **kw: "ok")

    bot = Chatbot("be nice")
    bot.send("one")
    assert bot.history == [
        {"role": "user", "content": "one"},
        {"role": "assistant", "content": "ok"},
    ]
    assert dojo_ai.calls[-1]["system"] == "be nice"


def test_trims():
    from main import Chatbot

    dojo_ai.fake(chat=lambda messages, **kw: "ok")

    bot = Chatbot("s", max_messages=4)
    for word in ["a", "b", "c"]:
        bot.send(word)
    assert len(bot.history) == 4
    assert bot.history[0] == {"role": "user", "content": "b"}, "Drop the oldest messages"
