age = int(input("Age: "))
tuesday = input("Is it Tuesday? (yes/no): ")

if age < 5:
    price = 0
elif age < 18:
    price = 8
elif age < 65:
    price = 12
else:
    price = 6

if tuesday == "yes" and price > 0:
    price = price - 2

print("Price:", price)
