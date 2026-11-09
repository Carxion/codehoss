# %%
def build_messages(history, user_input):
    return history + [{"role": "user", "content": user_input}]
