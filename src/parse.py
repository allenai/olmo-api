import datetime

def timedelta(s: str) -> datetime.timedelta:
    """
    Returns a datetime.timedelta from the given string, or raises a ValueError
    if the string is not a valid interval.

    The supported format is intentionally simple:
    - the unit must be a single character
    - the unit must be one of "h" for hours, "m" for minutes or "s" for seconds
    - the unit must be the last non-whitespace character in the string
    - the number must be a positive integer
    - compound expressions are not supported, i.e "1h30m"
    """
    number = int(s.strip()[:-1])
    if number < 0:
        raise ValueError(f"timedelta must be positive: {number}")

    unit = s.strip()[-1]
    match unit:
        case "h":
            return datetime.timedelta(hours=number)
        case "m":
            return datetime.timedelta(minutes=number)
        case "s":
            return datetime.timedelta(seconds=number)
        case _:
            raise ValueError(f"Invalid unit: {unit}")
