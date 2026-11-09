totals = {}

while True:
    command = input("> ").strip()
    parts = command.split()
    if parts == ["quit"]:
        print("Bye!")
        break
    elif parts == ["report"]:
        for category in sorted(totals):
            print(f"{category}: {totals[category]:.2f}")
        print(f"Total: {sum(totals.values()):.2f}")
    elif len(parts) == 3 and parts[0] == "add":
        try:
            amount = float(parts[2])
        except ValueError:
            print("Amount must be a number")
            continue
        totals[parts[1]] = totals.get(parts[1], 0) + amount
    else:
        print("Unknown command")
