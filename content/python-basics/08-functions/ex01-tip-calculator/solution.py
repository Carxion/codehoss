def calculate_tip(bill, percent):
    return round(bill * percent / 100, 2)


def split_bill(total, people):
    return round(total / people, 2)
