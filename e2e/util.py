from requests import Response

def last_response_line(r: Response) -> str:
    """Get the last line of a streaming response."""
    return list(r.text.splitlines())[-1]
