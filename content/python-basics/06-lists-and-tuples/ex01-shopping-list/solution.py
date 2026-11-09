shopping = ["milk", "eggs"]
shopping.append("bread")
shopping.remove("eggs")
shopping.insert(0, "apples")

print(len(shopping), "items:")
for item in shopping:
    print("-", item)
