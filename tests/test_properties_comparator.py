from pathlib import Path

from config_rationalizer.core.enums import ChangeType
from config_rationalizer.core.logging_config import configure_logging
from config_rationalizer.properties.comparator import (
    compare_properties,
)
from config_rationalizer.reporting.json_report import (
    comparison_to_dict,
)


FIXTURES = Path(__file__).parent / "fixtures"


def test_realistic_properties_comparison():
    audit = configure_logging(console=False)

    result = compare_properties(
        FIXTURES / "properties_before.properties",
        FIXTURES / "properties_after.properties",
        run_id="test-run",
        audit=audit,
    )

    assert result.status == "COMPLETED"
    assert result.delimiter == "="

    changes = {item.logical_path: item for item in result.changes}

    assert changes["server.port"].change_type == ChangeType.UNCHANGED

    assert (
        changes["spring.profiles.active"].change_type == ChangeType.VENDOR_VALUE_CHANGED
    )

    assert changes["changed.value"].change_type == ChangeType.VENDOR_VALUE_CHANGED

    assert changes["removed.value"].change_type == ChangeType.REMOVED_BY_VENDOR

    assert changes["new.value"].change_type == ChangeType.ADDED

    assert changes["application.name"].change_type == ChangeType.UNCHANGED


def test_removed_property_is_detected():
    audit = configure_logging(console=False)

    result = compare_properties(
        FIXTURES / "properties_before.properties",
        FIXTURES / "properties_removed.properties",
        run_id="test-run",
        audit=audit,
    )

    assert result.status == "COMPLETED"

    removed = [
        item
        for item in result.changes
        if item.change_type == ChangeType.REMOVED_BY_VENDOR
    ]

    assert len(removed) == 1
    assert removed[0].logical_path == "removed.value"


def test_whitespace_only_changes_are_unchanged(tmp_path):
    before = tmp_path / "before.properties"
    after = tmp_path / "after.properties"

    before.write_text(
        "key=value\n",
        encoding="utf-8",
    )

    after.write_text(
        "  key = value  \n",
        encoding="utf-8",
    )

    audit = configure_logging(console=False)

    result = compare_properties(
        before,
        after,
        run_id="test-run",
        audit=audit,
    )

    assert result.status == "COMPLETED"
    assert result.unchanged_count == 1


def test_no_delimiter_is_skipped(tmp_path):
    before = tmp_path / "before.properties"
    after = tmp_path / "after.properties"

    before.write_text(
        "this is not a property\n",
        encoding="utf-8",
    )

    after.write_text(
        "key=value\n",
        encoding="utf-8",
    )

    audit = configure_logging(console=False)

    result = compare_properties(
        before,
        after,
        run_id="test-run",
        audit=audit,
    )

    assert result.status == "SKIPPED"
    assert result.warnings


def test_delimiter_mismatch_is_error(tmp_path):
    before = tmp_path / "before.properties"
    after = tmp_path / "after.properties"

    before.write_text(
        "key=value\n",
        encoding="utf-8",
    )

    after.write_text(
        "key:value\n",
        encoding="utf-8",
    )

    audit = configure_logging(console=False)

    result = compare_properties(
        before,
        after,
        run_id="test-run",
        audit=audit,
    )

    assert result.status == "ERROR"
    assert result.errors
    assert "delimiter" in result.errors[0]


def test_json_report_contains_summary(tmp_path):
    audit = configure_logging(console=False)

    result = compare_properties(
        FIXTURES / "properties_before.properties",
        FIXTURES / "properties_after.properties",
        run_id="test-run",
        audit=audit,
    )

    report = comparison_to_dict(result)

    assert report["status"] == "COMPLETED"
    assert "summary" in report
    assert "changes" in report
    assert report["summary"]["total"] > 0
