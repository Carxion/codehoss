names = input("Names: ").split()
scores = [int(s) for s in input("Scores: ").split()]

for name, score in zip(names, scores):
    result = "pass" if score >= 50 else "fail"
    print(f"{name}: {score} {result}")

passed = [name for name, score in zip(names, scores) if score >= 50]
print("Passed:", ", ".join(passed))
