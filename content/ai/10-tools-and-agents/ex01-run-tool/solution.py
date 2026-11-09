# %%
TOOLS = {
    "add": lambda a, b: a + b,
    "multiply": lambda a, b: a * b,
}


def run_tool(call):
    name = call.get("tool")
    if name not in TOOLS:
        return f"Error: unknown tool {name!r}"
    try:
        return TOOLS[name](**call.get("args", {}))
    except Exception as e:
        return f"Error: {e}"


# %%
run_tool({"tool": "multiply", "args": {"a": 6, "b": 7}})
