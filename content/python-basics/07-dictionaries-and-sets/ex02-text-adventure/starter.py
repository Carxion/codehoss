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
    # TODO: handle "quit" (print Goodbye! and break)
    # TODO: handle "go <direction>"
    # TODO: anything else: print("I don't understand.")
