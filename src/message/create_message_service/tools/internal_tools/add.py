from pydantic_ai import Tool


def add_fn(x: int, y: int) -> int:
    """Adds two numbers together"""
    return x + y


Add = Tool(add_fn, takes_ctx=False)
