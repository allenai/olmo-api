from pydantic_ai import Tool


def make_person_fn(first: str, last: str) -> str:
    """Adds a user to the db"""
    return first + last


MakePerson = Tool(make_person_fn, takes_ctx=False)
