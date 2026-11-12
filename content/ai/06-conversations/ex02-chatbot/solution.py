# %%
import hoss_ai


class Chatbot:
    def __init__(self, system, max_messages=10):
        self.system = system
        self.max_messages = max_messages
        self.history = []

    def send(self, text):
        self.history.append({"role": "user", "content": text})
        reply = hoss_ai.chat(self.history, system=self.system)
        self.history.append({"role": "assistant", "content": reply})
        self.history = self.history[-self.max_messages :]
        return reply


# %%
bot = Chatbot("You are a cheerful bike shop assistant.")
bot.send("Hi, I'm Ada.")
bot.send("What's my name?")
