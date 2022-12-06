

from math import sqrt
from time import time


def next_highest_prime(n: int):
    while True:
        square = sqrt(n)
        if square.real.is_integer():
            return n
        else:
            n = n+1

print(next_highest_prime(3))
print(next_highest_prime(12))
print(next_highest_prime(29))
print(next_highest_prime(500))

