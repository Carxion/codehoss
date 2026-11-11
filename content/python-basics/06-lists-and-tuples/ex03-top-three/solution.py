line = input("Scores: ")

scores = [int(piece) for piece in line.split(",")]

top = sorted(scores, reverse=True)[:3]
print("Top 3:", ", ".join([str(s) for s in top]))
print("Lowest:", min(scores))
print("80 or more:", len([s for s in scores if s >= 80]))
