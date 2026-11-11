p1 = input("Player 1: ").strip().lower()
p2 = input("Player 2: ").strip().lower()

moves = ("rock", "paper", "scissors")
if p1 not in moves or p2 not in moves:
    print("Invalid move")
elif p1 == p2:
    print("Draw")
elif (
    (p1 == "rock" and p2 == "scissors")
    or (p1 == "scissors" and p2 == "paper")
    or (p1 == "paper" and p2 == "rock")
):
    print("Player 1 wins")
else:
    print("Player 2 wins")
