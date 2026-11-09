import json


def add_contact(book, name, phone):
    book[name] = phone


def save_contacts(book, path):
    with open(path, "w") as f:
        json.dump(book, f)


def load_contacts(path):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
