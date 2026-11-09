# %%
import dojo_ai


def summarize_reviews(reviews):
    lines = [f"{i}. {review}" for i, review in enumerate(reviews, start=1)]
    prompt = "Summarize these reviews in one sentence:\n" + "\n".join(lines)
    return dojo_ai.chat(prompt)


# %%
summarize_reviews(["Great bike, very light.", "Delivery took two weeks.", "Love the colour!"])
