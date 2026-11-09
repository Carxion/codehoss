count = int(input("How many scores? "))
scores = []

for _ in range(count):
    scores.append(int(input("Score: ")))

print("Highest:", max(scores))
print("Lowest:", min(scores))
print("Average:", round(sum(scores) / len(scores), 1))
