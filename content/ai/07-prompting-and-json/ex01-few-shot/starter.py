# %%
import dojo_ai

INSTRUCTION = "Classify the sentiment as positive, negative or neutral."
EXAMPLES = [("I love it!", "positive"), ("It broke after a day.", "negative")]


def few_shot_prompt(instruction, examples, text):
    # TODO
    return ""


def classify(text):
    # TODO
    return ""


# %%
print(few_shot_prompt(INSTRUCTION, EXAMPLES, "The box was blue."))
