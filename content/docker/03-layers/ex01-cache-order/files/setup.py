"""Pretend this is slow: installing packages, downloading models..."""
import time

time.sleep(3)
words = open("words.txt").read().split()
with open("index.txt", "w") as f:
    f.write("\n".join(sorted(set(words))))
print("setup done")
