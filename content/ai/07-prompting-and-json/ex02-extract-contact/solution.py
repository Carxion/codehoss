# %%
import json

import dojo_ai

PROMPT = 'Return JSON with keys "name" and "email" for the person in this text: {text}'


def extract_contact(text):
    for _ in range(2):
        reply = dojo_ai.chat(PROMPT.format(text=text), json=True)
        try:
            data = json.loads(reply)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and "name" in data and "email" in data:
            return {"name": data["name"], "email": data["email"]}
    return None


# %%
extract_contact("Hi, this is Grace Hopper. Write to me at grace@navy.mil anytime.")
