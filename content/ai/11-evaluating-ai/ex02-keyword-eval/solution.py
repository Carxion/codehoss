# %%
import hoss_ai

CASES = [
    {"question": "How long is the bike return window?", "keywords": ["30", "days"]},
    {"question": "How long are frames under warranty?", "keywords": ["lifetime"]},
]


def keyword_score(answer, keywords):
    if not keywords:
        return 0.0
    return sum(k.lower() in answer.lower() for k in keywords) / len(keywords)


def run_eval(cases):
    if not cases:
        return 0.0
    scores = [keyword_score(hoss_ai.chat(c["question"]), c["keywords"]) for c in cases]
    return sum(scores) / len(scores)


# %%
run_eval(CASES)
