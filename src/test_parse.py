from . import parse
from datetime import timedelta
from dataclasses import dataclass

import pytest

def test_parse_valid_timedelta():
    tests = [
        ("1h", timedelta(hours=1)),
        ("1m", timedelta(minutes=1)),
        ("1s", timedelta(seconds=1)),
        ("42h", timedelta(hours=42)),
        ("42m", timedelta(minutes=42)),
        ("42s", timedelta(seconds=42)),
    ]
    for (input, expected) in tests:
        assert parse.timedelta_from_str(input) == expected, f"Failed to parse timedelta parse.timedelta(\"{input}\") != {expected}"

def test_parse_invalid_timedelta():
    tests = [
        "",
        "1",
        "1w",
        "1 hour",
        "1 minute",
        "1 second",
        "1 month"
        "1d30m",
        "-1d",
        "1.5d",
    ]
    for input in tests:
        with pytest.raises(ValueError):
            parse.timedelta_from_str(input)

@dataclass
class DatachipTestCase:
    name: str
    input: str
    expected_output: str
    chips: dict[str, str]

def test_parse_and_replace_datachips():
    tests = [
        # A typical case with several well-formed datachips
        DatachipTestCase(
            "typical",
            """
<h1>Hey <span data-datachip-id="to">To</span>,</h1>
<p>My name is <span data-datachip-id="from">From</span>.</p>
<p>Do you like to <strong><span data-datachip-id="activity">Activity</span>?</strong></p>
Best,<br>
<span data-datachip-id="from">From</span>
            """.strip(),
            """
<h1>Hey Murphy,</h1>
<p>My name is Logan.</p>
<p>Do you like to <strong>dig holes?</strong></p>
Best,<br>
Logan
            """.strip(),
            { "to": "Murphy", "from": "Logan", "activity": "dig holes" }
        ),
        # A datachip with a child tag
        DatachipTestCase(
            "nested_marquee",
            """Hi <span data-datachip-id="name"><marquee>Name</marquee></span>!""",
            """Hi Murphy!""",
            { "name": "Murphy" }
        ),
        # Recursive, nested datachips
        DatachipTestCase(
            "nested_chip",
            """Hi <span data-datachip-id="name1"><span data-datachip-id="name2">Name</span></span>!""",
            """Hi Murphy!""",
            { "name1": "Murphy", "name2": "Logan" }
        ),
        # Emojis
        DatachipTestCase(
            "emoji",
            """👋 <span data-datachip-id="name">Name</span>""",
            """👋 Murphy""",
            { "name": "Murphy" }
        ),
        # HTML Entities
        DatachipTestCase(
            "emoji",
            """Hi &ldquo;<span data-datachip-id="name">Name</span>&rdquo;""",
            """Hi &ldquo;Murphy&rdquo;""",
            { "name": "Murphy" }
        ),
    ]
    for test in tests:
        content = parse.MessageContent(test.input)
        for dc in content.datachips():
            dc.tag.replace_with(test.chips[dc.id()])
        assert content.html() == test.expected_output, f"Failed to parse datachips for test {test.name}"
