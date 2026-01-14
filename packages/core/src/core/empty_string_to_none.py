def empty_string_to_none(value: str | None) -> str | None:
    if value is None:
        return value

    if value.strip() == "":
        return None

    return value
