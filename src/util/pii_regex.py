import re

EMAIL_REGEX = r"[.\s@,?!;:)(]*([^\s@]+@[^\s@,?!;:)(]+?)[.\s@,?!;:)(]?[\s\n\r]"

PHONE_NUMBER_REGEX = r"\s+\(?(\d{3})\)?[-\. ]*(\d{3})[-. ]?(\d{4})"

IP_ADDRESS_REGEX = r"(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"


combined_pii_regex = re.compile(
    f"{EMAIL_REGEX}|{PHONE_NUMBER_REGEX}|{IP_ADDRESS_REGEX}"
)


def does_contain_pii(string_to_check) -> bool:
    return combined_pii_regex.match(string_to_check) is not None
