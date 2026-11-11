def slugify(title):
    chars = []
    for ch in title.lower():
        if ch.isalnum():
            chars.append(ch)
        elif chars and chars[-1] != "-":
            chars.append("-")
    return "".join(chars).strip("-")


print(slugify("Hello, World!"))
