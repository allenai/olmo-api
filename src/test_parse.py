from dataclasses import dataclass
from datetime import timedelta

import pytest

from . import parse
from .dao.datachip import DatachipRef


def test_parse_valid_timedelta():
    tests = [
        ("1h", timedelta(hours=1)),
        ("1m", timedelta(minutes=1)),
        ("1s", timedelta(seconds=1)),
        ("42h", timedelta(hours=42)),
        ("42m", timedelta(minutes=42)),
        ("42s", timedelta(seconds=42)),
    ]
    for input, expected in tests:
        assert parse.timedelta_from_str(input) == expected, (
            f'Failed to parse timedelta parse.timedelta("{input}") != {expected}'
        )


def test_parse_invalid_timedelta():
    tests = [
        "",
        "1",
        "1w",
        "1 hour",
        "1 minute",
        "1 second",
        "1 month1d30m",
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
    chips: dict[DatachipRef, str]
    should_raise: bool = False


def test_parse_and_replace_datachips():
    tests = [
        # A typical case with several well-formed datachips
        DatachipTestCase(
            "typical",
            """
Hi :sams@allenai.org/to,

My name is :sams@allenai.org/from.
Do you like to <strong>:murphy@allenai.org/activity</strong>?

Best,
:sams@allenai.org/from
            """.strip(),
            """
Hi Murphy,

My name is Logan.
Do you like to <strong>dig elaborate, muddy holes to bury valuable bones, treasure and other amassed, random things in the ground</strong>?

Best,
Logan
            """.strip(),
            {
                DatachipRef("sams@allenai.org/to"): "Murphy",
                DatachipRef("sams@allenai.org/from"): "Logan",
                DatachipRef(
                    "murphy@allenai.org/activity"
                ): "dig elaborate, muddy holes to bury valuable bones, treasure and other amassed, random things in the ground",
            },
        ),
        # Emojis
        DatachipTestCase(
            "emoji",
            """👋 :sams@allenai.org/name""",
            "👋 Murphy",
            {DatachipRef("sams@allenai.org/name"): "Murphy"},
        ),
        DatachipTestCase(
            "leading",
            """:sams@allenai.org/name says hello""",
            "Murphy says hello",
            {DatachipRef("sams@allenai.org/name"): "Murphy"},
        ),
        DatachipTestCase(
            "trailing",
            """my name is :sams@allenai.org/name""",
            "my name is Murphy",
            {DatachipRef("sams@allenai.org/name"): "Murphy"},
        ),
        DatachipTestCase("none", """Hi there!""", "Hi there!", {}),
        DatachipTestCase(
            "missing",
            """my name is :sams@allenai.org/name""",
            "",
            {},
            True,
        ),
    ]
    for test in tests:
        msg = parse.MessageContent(test.input)
        if test.should_raise:
            with pytest.raises(ValueError):
                msg.replace_datachips(test.chips)
        else:
            details = f"Failed to parse datachips for test {test.name}"
            assert msg.replace_datachips(test.chips) == test.expected_output, details
