# %%
import json

import dojo_ai

TOOLS = {
    "add": lambda a, b: a + b,
    "multiply": lambda a, b: a * b,
}

SYSTEM = """You can use these tools:
- add(a, b): add two numbers
- multiply(a, b): multiply two numbers
Reply with JSON only: {"tool": name, "args": {...}} to use a tool,
or {"answer": text} when you know the final answer."""


def run_tool(call):
    name = call.get("tool")
    if name not in TOOLS:
        return f"Error: unknown tool {name!r}"
    try:
        return TOOLS[name](**call.get("args", {}))
    except Exception as e:
        return f"Error: {e}"


def agent(question, max_steps=5):
    # TODO
    return "I couldn't finish."


# %%
agent("What is (3 + 4) times 6?")
