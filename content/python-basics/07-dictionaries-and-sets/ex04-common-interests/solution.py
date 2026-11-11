you = input("You: ")
them = input("Them: ")

mine = {i.strip().lower() for i in you.split(",")}
theirs = {i.strip().lower() for i in them.split(",")}


print("Both:", ", ".join(sorted(mine & theirs)) or "(none)")
print("Only you:", ", ".join(sorted(mine - theirs)) or "(none)")
print("Only them:", ", ".join(sorted(theirs - mine)) or "(none)")
