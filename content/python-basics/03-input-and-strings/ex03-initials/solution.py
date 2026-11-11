name = input("Full name: ")

first, last = name.split()

print(f"Initials: {first[0].upper()}.{last[0].upper()}.")
print(f"Username: {first.lower()}.{last.lower()}")
