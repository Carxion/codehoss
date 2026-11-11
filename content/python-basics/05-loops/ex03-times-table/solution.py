size = int(input("Size: "))

for row in range(1, size + 1):
    row_text = ""
    for col in range(1, size + 1):
        row_text += f"{row * col:4}"
    print(row_text)
