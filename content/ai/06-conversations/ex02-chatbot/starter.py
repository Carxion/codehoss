# %%
import dojo_ai


class Chatbot:
    def __init__(self, system, max_messages=10):
        self.system = system
        self.max_messages = max_messages
        self.history = []

    def send(self, text):
        # TODO
        return ""


# %%
bot = Chatbot("You are a cheerful bike shop assistant.")
bot.send("Hi, I'm Ada.")
bot.send("What's my name?")
