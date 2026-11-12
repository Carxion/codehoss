# %%
import re

import hoss_ai

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")


def redact(text):
    text = EMAIL.sub("[EMAIL]", text)
    return PHONE.sub("[PHONE]", text)

BLOCKED = ["ignore previous instructions", "ignore all instructions", "reveal your system prompt"]
REFUSAL = "Sorry, I can't help with that."


def safe_chat(prompt):
    # TODO
    return ""


# %%
safe_chat("My email is ada@lumen.example. When does my bike arrive?")
