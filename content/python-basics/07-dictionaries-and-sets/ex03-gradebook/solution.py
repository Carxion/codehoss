book = {}

while True:
    line = input("Entry: ")
    if not line:
        break
    name, score = line.split()
    book.setdefault(name, []).append(int(score))

for name, scores in book.items():
    print(f"{name}: {len(scores)} scores, average {sum(scores) / len(scores):.1f}")
