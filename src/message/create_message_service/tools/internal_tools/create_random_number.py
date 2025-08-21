import random

from pydantic_ai import Tool


def create_random_number() -> str:
    """Generates a random number between 1 and 10"""
    return str(random.randrange(1, 10))


CreateRandomNumber = Tool(create_random_number, takes_ctx=False)
