def has_digit(password):
    for ch in password:
        if ch.isdigit():
            return True
    return False


def has_upper(password):
    for ch in password:
        if ch.isupper():
            return True
    return False


def strength(password):
    score = 0
    if len(password) >= 8:
        score += 1
    if has_digit(password):
        score += 1
    if has_upper(password):
        score += 1
    for ch in password:
        if ch in "!@#$%&*":
            score += 1
            break
    if score == 4:
        return "strong"
    elif score >= 2:
        return "medium"
    return "weak"


print(strength("Tr0ub4dor&3"))
