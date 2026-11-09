# %%
import re

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")


def redact(text):
    text = EMAIL.sub("[EMAIL]", text)
    return PHONE.sub("[PHONE]", text)


# %%
redact("Call +1 (555) 010-9999 or mail ada@lumen.example")
