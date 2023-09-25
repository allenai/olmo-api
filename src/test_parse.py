from . import parse
from datetime import timedelta

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
        assert parse.timedelta(input) == expected, f"Failed to parse timedelta parse.timedelta(\"{input}\") != {expected}"

def test_parse_invalid_timedelta():
    tests = [
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
            parse.timedelta(input)
