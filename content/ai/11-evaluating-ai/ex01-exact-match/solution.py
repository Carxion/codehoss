# %%
def exact_match(predictions, answers):
    if not answers:
        return 0.0
    matches = sum(p.strip().lower() == a.strip().lower() for p, a in zip(predictions, answers))
    return matches / len(answers)
