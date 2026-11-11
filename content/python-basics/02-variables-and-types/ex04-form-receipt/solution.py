price_text = "4.25"
quantity_text = "3"

price = float(price_text)
quantity = int(quantity_text)

total = round(price * quantity, 2)

print(quantity, "x", price, "=", total)
