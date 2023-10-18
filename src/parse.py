import datetime
import bs4

from dataclasses import dataclass
from typing import Generator

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
class DatachipTag:
    """
    Datachips are embedded into messages as HTML tags of the form:

        <span data-datachip-id=":id">:name</span>

    The :name is a placeholder for display purposes only. The :id value references
    the corresponding datachip.
    """
    tag: bs4.Tag

    def id(self) -> str:
        return self.tag.attrs["data-datachip-id"]

    def name(self) -> str:
        return self.tag.get_text()

    @staticmethod
    def selector(tag: bs4.Tag) -> bool:
        return tag.name == "span" and tag.has_attr("data-datachip-id")

class MessageContent:
    """
    MessageContent is a wrapper that allows for message content to be parsed
    as HTML content, as to replace datachip references with their corresponding values.

    Usage:

        # Parse content
        content = parse.MessageContent(html)

        # Replace datachips
        for chip in content.datachips():
            content.replace(chip, chips[chip.id()])

        # Obtain the updated HTML
        content.html()
    """
    def __init__(self, html: str):
        self.soup = bs4.BeautifulSoup(html, "html.parser")

    def datachips(self) -> Generator[DatachipTag, None, None]:
        for tag in self.soup.find_all(DatachipTag.selector):
            yield DatachipTag(tag)

    def html(self) -> str:
        return self.soup.decode(formatter="html5")

