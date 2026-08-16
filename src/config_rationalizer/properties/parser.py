from dataclasses import dataclass
from pathlib import Path


class PropertiesParseError(Exception):
    """Raised when a properties file cannot be safely parsed."""


@dataclass(frozen=True)
class PropertyEntry:
    key: str
    value: str
    line_number: int
    raw_line: str


@dataclass
class ParsedProperties:
    path: Path
    delimiter: str
    entries: dict[str, PropertyEntry]
    warnings: list[str]


def _is_comment(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("#") or stripped.startswith("!")


def _first_delimiter_position(line: str) -> tuple[str | None, int | None]:
    positions = [
        (line.find("="), "="),
        (line.find(":"), ":"),
    ]

    valid = [
        (position, delimiter) for position, delimiter in positions if position >= 0
    ]

    if not valid:
        return None, None

    position, delimiter = min(valid, key=lambda item: item[0])
    return delimiter, position


def detect_delimiter(lines: list[str]) -> str | None:
    for line in lines:
        if not line.strip() or _is_comment(line):
            continue

        delimiter, _ = _first_delimiter_position(line)

        if delimiter is not None:
            return delimiter

    return None


def _split_property(
    line: str,
    delimiter: str,
    line_number: int,
) -> tuple[str, str]:
    position = line.find(delimiter)

    if position < 0:
        raise PropertiesParseError(
            f"Line {line_number} does not contain the file delimiter {delimiter!r}."
        )

    key = line[:position].strip()
    value = line[position + 1 :].strip()

    if not key:
        raise PropertiesParseError(
            f"Line {line_number} contains an empty property key."
        )

    return key, value


def parse_properties(path: Path) -> ParsedProperties:
    lines = path.read_text(encoding="utf-8").splitlines()

    delimiter = detect_delimiter(lines)

    if delimiter is None:
        raise PropertiesParseError(f"No properties delimiter found in {path}")

    entries: dict[str, PropertyEntry] = {}

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()

        if not stripped or _is_comment(line):
            continue

        detected_delimiter, _ = _first_delimiter_position(line)

        if detected_delimiter != delimiter:
            raise PropertiesParseError(
                f"Line {line_number} uses delimiter "
                f"{detected_delimiter!r}, expected {delimiter!r}."
            )

        key, value = _split_property(
            line,
            delimiter,
            line_number,
        )

        if key in entries:
            raise PropertiesParseError(
                f"Duplicate property key {key!r} "
                f"on line {line_number}; "
                f"first occurrence was on line "
                f"{entries[key].line_number}."
            )

        entries[key] = PropertyEntry(
            key=key,
            value=value,
            line_number=line_number,
            raw_line=line,
        )

    return ParsedProperties(
        path=path,
        delimiter=delimiter,
        entries=entries,
        warnings=[],
    )
