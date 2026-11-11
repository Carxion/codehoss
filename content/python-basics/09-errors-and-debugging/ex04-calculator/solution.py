def calculate(text):
    parts = text.split()
    if len(parts) != 3:
        raise ValueError("use the form: number operator number")
    left, op, right = parts
    numbers = []
    for part in (left, right):
        try:
            numbers.append(float(part))
        except ValueError:
            raise ValueError(f"not a number: {part}")
    a, b = numbers
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        return a / b
    raise ValueError(f"unknown operator: {op}")


def answer(text):
    try:
        result = calculate(text)
    except ValueError as e:
        return f"Error: {e}"
    except ZeroDivisionError:
        return "Error: can't divide by zero"
    return f"= {result:g}"


for sum_text in ["8 / 2", "2 ^ 3", "1 / 0", "seven * 2", "5 +"]:
    print(sum_text, "->", answer(sum_text))
