from pathlib import Path

import pytest

from config_rationalizer.properties.parser import (
    PropertiesParseError,
    parse_properties,
)


def write_file(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "test.properties"
    path.write_text(content, encoding="utf-8")
    return path


def test_parser_uses_equals_delimiter():
    path = Path(__file__).parent / "fixtures" / "properties_before.properties"

    result = parse_properties(path)

    assert result.delimiter == "="
    assert result.entries["server.port"].value == "8080"


def test_colon_inside_value_is_not_a_delimiter(tmp_path):
    path = write_file(
        tmp_path,
        "service.url=http://localhost:8080/api\n",
    )

    result = parse_properties(path)

    assert result.delimiter == "="
    assert result.entries["service.url"].value == ("http://localhost:8080/api")


def test_equals_inside_value_is_not_a_delimiter(tmp_path):
    path = write_file(
        tmp_path,
        "token=value=with=equals\n",
    )

    result = parse_properties(path)

    assert result.entries["token"].value == "value=with=equals"


def test_whitespace_is_ignored(tmp_path):
    path = write_file(
        tmp_path,
        "  key  =   value   \n",
    )

    result = parse_properties(path)

    assert result.entries["key"].value == "value"


def test_comments_and_blank_lines_are_ignored(tmp_path):
    path = write_file(
        tmp_path,
        """
# comment
   # indented comment
! another comment

key=value
""",
    )

    result = parse_properties(path)

    assert list(result.entries) == ["key"]


def test_empty_value_is_valid(tmp_path):
    path = write_file(
        tmp_path,
        "key=\n",
    )

    result = parse_properties(path)

    assert result.entries["key"].value == ""


def test_duplicate_key_is_error(tmp_path):
    path = write_file(
        tmp_path,
        "key=one\nkey=two\n",
    )

    with pytest.raises(
        PropertiesParseError,
        match="Duplicate property key",
    ):
        parse_properties(path)


def test_no_delimiter_is_error_for_parser(tmp_path):
    path = write_file(
        tmp_path,
        "this-is-not-a-property\n",
    )

    with pytest.raises(
        PropertiesParseError,
        match="No properties delimiter found",
    ):
        parse_properties(path)


def test_colon_delimiter(tmp_path):
    path = write_file(
        tmp_path,
        """
first:value
second:another:value
""",
    )

    result = parse_properties(path)

    assert result.delimiter == ":"
    assert result.entries["first"].value == "value"
    assert result.entries["second"].value == "another:value"


def test_mixed_structural_delimiters_are_rejected(tmp_path):
    path = write_file(
        tmp_path,
        """
first=value
second:value
""",
    )

    with pytest.raises(
        PropertiesParseError,
        match="uses delimiter",
    ):
        parse_properties(path)
