import hoss_ai


def test_remembers():
    from main import Chatbot

    hoss_ai.fake(chat=lambda messages, **kw: f"reply {len(messages)}")

    bot = Chatbot("be nice")
    assert bot.send("Hi") == "reply 1"
    assert bot.send("Again") == "reply 3", "Send the whole history each time"
