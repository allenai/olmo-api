import random

from pydantic_ai import Tool


def create_random_number() -> int:
    """Generates a random number between 1 and 10"""
    return random.randrange(1, 10)


CreateRandomNumber = Tool(create_random_number, takes_ctx=False)
