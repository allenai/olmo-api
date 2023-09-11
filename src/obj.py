import string
import secrets

# obj.ID is a unique identifier for an object.
ID = str

def NewID(prefix: str) -> ID:
    """
    Returns a unique ID that's easy to copy and paste because it's short and
    avoids producing embarrassing words from random runs of letters.

    Based off of: https://github.com/allenai/emory/blob/main/api/docid/docid.go.
    """
    id = ""
    while len(id) <= 8:
        id += string.ascii_uppercase[secrets.randbelow(len(string.ascii_uppercase))]
        id += string.digits[secrets.randbelow(len(string.digits))]
    return f"{prefix}_{id}"

