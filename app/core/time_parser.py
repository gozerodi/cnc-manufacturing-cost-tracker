"""
Time input format: dot-separated parts.
- 2 parts => MM.SS  (e.g. "1.30" -> 90 seconds)
- 3 parts => HH.MM.SS (e.g. "01.15.00" -> 4500 seconds)
"""


class TimeParseError(ValueError):
    pass


def parse_time_to_seconds(text: str) -> int:
    if text is None:
        raise TimeParseError("Time cannot be empty.")

    text = text.strip()
    if not text:
        raise TimeParseError("Time cannot be empty.")

    parts = text.split(".")
    if len(parts) not in (2, 3):
        raise TimeParseError(
            "Invalid time format. Enter 2 parts (MM.SS) or 3 parts (HH.MM.SS)."
        )

    if not all(part.isdigit() for part in parts):
        raise TimeParseError("Time can only contain digits and dots.")

    if len(parts) == 2:
        hours = 0
        minutes, seconds = int(parts[0]), int(parts[1])
    else:
        hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
        if not (0 <= minutes <= 59):
            raise TimeParseError("Minutes must be between 0 and 59.")

    if not (0 <= seconds <= 59):
        raise TimeParseError("Seconds must be between 0 and 59.")

    return hours * 3600 + minutes * 60 + seconds


def is_valid_time_input(text: str) -> bool:
    try:
        parse_time_to_seconds(text)
        return True
    except TimeParseError:
        return False


def format_seconds(total_seconds: int) -> str:
    if total_seconds is None or total_seconds < 0:
        raise TimeParseError("Time cannot be negative.")

    hours, remainder = divmod(int(total_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}.{minutes:02d}.{seconds:02d}"
    return f"{minutes}.{seconds:02d}"
