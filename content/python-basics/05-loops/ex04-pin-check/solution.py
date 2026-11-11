correct = "4321"
granted = False

for attempt in range(1, 4):
    pin = input("PIN: ")
    if pin == correct:
        print("Access granted")
        granted = True
        break
    print(f"Wrong PIN. Attempts left: {3 - attempt}")

if not granted:
    print("Card blocked")
