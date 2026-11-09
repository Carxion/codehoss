rooms = {
    "hall": {
        "description": "You are in a dusty hall.",
        "exits": {"north": "library", "east": "kitchen"},
    },
    "library": {
        "description": "Books line the walls.",
        "exits": {"south": "hall"},
    },
    "kitchen": {
        "description": "It smells of old bread.",
        "exits": {"west": "hall"},
    },
}

current = "hall"
print(rooms[current]["description"])

while True:
    command = input("> ").strip().lower()
    if command == "quit":
        print("Goodbye!")
        break
    elif command.startswith("go "):
        direction = command[3:]
        exits = rooms[current]["exits"]
        if direction in exits:
            current = exits[direction]
            print(rooms[current]["description"])
        else:
            print("You can't go that way.")
    else:
        print("I don't understand.")
