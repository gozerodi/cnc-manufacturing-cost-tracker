import pytest

from app.core.time_parser import (
    TimeParseError,
    format_seconds,
    is_valid_time_input,
    parse_time_to_seconds,
)


@pytest.mark.parametrize(
    "text,expected_seconds",
    [
        ("0.45", 45),
        ("1.30", 90),
        ("01.15.00", 4500),
        ("00.00", 0),
        ("0.00.05", 5),
        ("2.00", 120),
        ("10.05.09", 36309),
    ],
)
def test_parse_valid_inputs(text, expected_seconds):
    assert parse_time_to_seconds(text) == expected_seconds


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        None,
        "45",
        "1.2.3.4",
        "1.60",
        "1.99.00",
        "01.60.00",
        "abc",
        "1.a",
        "-1.30",
        "1.-30",
        "1..30",
    ],
)
def test_parse_invalid_inputs(text):
    with pytest.raises(TimeParseError):
        parse_time_to_seconds(text)


@pytest.mark.parametrize(
    "text,valid",
    [
        ("0.45", True),
        ("1.30", True),
        ("01.15.00", True),
        ("1.60", False),
        ("abc", False),
    ],
)
def test_is_valid_time_input(text, valid):
    assert is_valid_time_input(text) is valid


@pytest.mark.parametrize(
    "seconds,expected_text",
    [
        (45, "0.45"),
        (90, "1.30"),
        (4500, "1.15.00"),
        (0, "0.00"),
        (5, "0.05"),
        (36309, "10.05.09"),
    ],
)
def test_format_seconds(seconds, expected_text):
    assert format_seconds(seconds) == expected_text


def test_format_seconds_negative_raises():
    with pytest.raises(TimeParseError):
        format_seconds(-1)


def test_round_trip():
    for seconds in (0, 5, 45, 60, 90, 3599, 3600, 4500, 36309):
        text = format_seconds(seconds)
        assert parse_time_to_seconds(text) == seconds
