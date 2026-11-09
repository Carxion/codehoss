# %%
import dojo_ai

INSTRUCTION = "Classify the sentiment as positive, negative or neutral."
EXAMPLES = [("I love it!", "positive"), ("It broke after a day.", "negative")]


def few_shot_prompt(instruction, examples, text):
    blocks = [instruction]
    blocks += [f"Input: {inp}\nOutput: {out}" for inp, out in examples]
    blocks.append(f"Input: {text}\nOutput:")
    return "\n\n".join(blocks)


def classify(text):
    return dojo_ai.chat(few_shot_prompt(INSTRUCTION, EXAMPLES, text)).strip().lower()


# %%
print(few_shot_prompt(INSTRUCTION, EXAMPLES, "The box was blue."))
