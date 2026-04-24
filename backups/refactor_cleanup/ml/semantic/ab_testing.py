import random


def choose_variant(a: str, b: str):
    if random.random() < 0.5:
        return a, "A"
    return b, "B"
