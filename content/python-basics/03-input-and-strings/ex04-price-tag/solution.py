item = input("Item: ")
price = float(input("Price: "))
quantity = int(input("Quantity: "))

total = price * quantity

print(item.upper())
print(f"Price: ${price:.2f}")
print(f"Total: ${total:,.2f}")
