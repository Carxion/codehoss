secret = 7
guesses = 0

while True:
    guess = int(input("Your guess: "))
    guesses = guesses + 1
    if guess < secret:
        print("Too low!")
    elif guess > secret:
        print("Too high!")
    else:
        print(f"Correct! Guesses: {guesses}")
        break
