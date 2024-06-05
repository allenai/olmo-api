import datetime
import re
from .dao.datachip import DatachipRef

from dataclasses import dataclass

def timedelta_from_str(s: str) -> datetime.timedelta:
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
    if number <= 0:
        raise ValueError(f"timedelta must be a positive, non-zero integer: {number}")

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

@dataclass
class DatachipPlaceholder:
    """
    Datachips are embedded into messages like emojis:

        :creator/name

    At inference time the placeholder is replaced with the corresponding value
    that's stored in the database.

    This is a convenience mechanism for embedding frequently referenced and/or
    long values.
    """
    match: re.Match
    offset: int = 0

    @property
    def creator(self):
        return self.match.group("creator")

    @property
    def name(self):
        return self.match.group("name")

    @property
    def ref(self) -> DatachipRef:
        return self.match.group("ref")

    def __len__(self):
        return self.match.end() - self.match.start()

    def replace_with(self, content: str, value: str) -> str:
        """
        Returns a new string with the datachip replaced with the given value.
        """
        return content[:self.match.start() + self.offset] + value + content[self.match.end() + self.offset:]

class MessageContent:
    """
    MessageContent is a wrapper around message content that provides an API for
    finding and replacing datachips.
    """
    def __init__(self, content: str):
        self.content = content
        self.datachips = []
        for match in re.finditer(r"\B:(?P<ref>(?P<creator>[^:/]+)/(?P<name>\w+?))\b", content):
            self.datachips.append(DatachipPlaceholder(match))

    def replace_datachips(self, chips: dict[DatachipRef, str]) -> str:
        """
        Returns a new string with all datachips replaced with their values.
        """
        content = self.content
        for idx, dcp in enumerate(self.datachips):
            if dcp.ref not in chips:
                raise ValueError(f"Missing datachip value for \"{dcp.ref}\"")
            content = dcp.replace_with(content, chips[dcp.ref])
            # Update the offsets of all subsequent datachips
            for sibling in self.datachips[idx + 1:]:
                sibling.offset += len(chips[dcp.ref]) - len(dcp)
        return content

