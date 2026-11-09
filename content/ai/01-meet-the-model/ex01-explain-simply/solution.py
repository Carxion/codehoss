# %%
import dojo_ai

SYSTEM = "You explain things to a 10-year-old in two short sentences."


def explain_simply(topic):
    return dojo_ai.chat(f"Explain {topic}.", system=SYSTEM).strip()


# %%
explain_simply("gravity")
