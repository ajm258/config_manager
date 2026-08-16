from pathlib import Path

from config_rationalizer.core.logging_config import (
    configure_logging,
)
from config_rationalizer.properties.rationalizer import (
    GENERATED_MARKER,
    rationalize_properties_directory,
)


def create_properties(
    path: Path,
    content: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        content,
        encoding="utf-8",
    )


def test_rationalization_preserves_before_values_and_adds_vendor_properties(
    tmp_path,
):
    before = tmp_path / "before"
    after = tmp_path / "after"
    candidate = tmp_path / "candidate"

    create_properties(
        before / "spring-beans.properties",
        ("# Original comment\nunchanged=value\nchanged=original\nremoved=keep-me\n"),
    )

    create_properties(
        after / "spring-beans.properties",
        ("# Vendor file\nunchanged=value\nchanged=vendor\nadded=vendor-value\n"),
    )

    audit = configure_logging(console=False)

    result = rationalize_properties_directory(
        before,
        after,
        candidate,
        run_id="test-run",
        audit=audit,
    )

    assert result.status == "COMPLETED"

    output = (candidate / "spring-beans.properties").read_text(encoding="utf-8")

    assert "# Original comment" in output
    assert "unchanged=value" in output
    assert "changed=original" in output
    assert "removed=keep-me" in output

    assert "changed=vendor" not in output

    assert GENERATED_MARKER in output
    assert "added=vendor-value" in output


def test_before_only_file_is_retained(tmp_path):
    before = tmp_path / "before"
    after = tmp_path / "after"
    candidate = tmp_path / "candidate"

    create_properties(
        before / "nested" / "old.properties",
        "old.property=value\n",
    )

    create_properties(
        after / "main.properties",
        "new.property=value\n",
    )

    audit = configure_logging(console=False)

    result = rationalize_properties_directory(
        before,
        after,
        candidate,
        run_id="test-run",
        audit=audit,
    )

    assert result.status == "COMPLETED"

    old_file = candidate / "nested" / "old.properties"

    new_file = candidate / "main.properties"

    assert old_file.exists()
    assert new_file.exists()

    assert old_file.read_text(encoding="utf-8") == "old.property=value\n"


def test_after_only_file_is_added(tmp_path):
    before = tmp_path / "before"
    after = tmp_path / "after"
    candidate = tmp_path / "candidate"

    create_properties(
        before / "existing.properties",
        "existing=value\n",
    )

    create_properties(
        after / "new.properties",
        "vendor.property=value\n",
    )

    audit = configure_logging(console=False)

    result = rationalize_properties_directory(
        before,
        after,
        candidate,
        run_id="test-run",
        audit=audit,
    )

    assert result.status == "COMPLETED"

    new_file = candidate / "new.properties"

    assert new_file.exists()
    assert new_file.read_text(encoding="utf-8") == "vendor.property=value\n"


def test_recursive_relative_paths_are_preserved(tmp_path):
    before = tmp_path / "before"
    after = tmp_path / "after"
    candidate = tmp_path / "candidate"

    relative = Path("deep") / "nested" / "config.properties"

    create_properties(
        before / relative,
        "key=before\n",
    )

    create_properties(
        after / relative,
        "key=after\n",
    )

    audit = configure_logging(console=False)

    result = rationalize_properties_directory(
        before,
        after,
        candidate,
        run_id="test-run",
        audit=audit,
    )

    assert result.status == "COMPLETED"

    candidate_file = candidate / relative

    assert candidate_file.exists()
    assert candidate_file.read_text(encoding="utf-8") == "key=before\n"


def test_multiple_vendor_additions_are_appended(tmp_path):
    before = tmp_path / "before"
    after = tmp_path / "after"
    candidate = tmp_path / "candidate"

    create_properties(
        before / "config.properties",
        ("first=one\nsecond=two\n"),
    )

    create_properties(
        after / "config.properties",
        ("first=one\nsecond=two\nthird=three\nfourth=four\n"),
    )

    audit = configure_logging(console=False)

    rationalize_properties_directory(
        before,
        after,
        candidate,
        run_id="test-run",
        audit=audit,
    )

    output = (candidate / "config.properties").read_text(encoding="utf-8")

    assert output.index("first=one") < output.index("second=two")

    assert output.index("second=two") < output.index(GENERATED_MARKER)

    assert output.index(GENERATED_MARKER) < output.index("third=three")

    assert output.index("third=three") < output.index("fourth=four")


def test_original_before_file_is_not_modified(tmp_path):
    before = tmp_path / "before"
    after = tmp_path / "after"
    candidate = tmp_path / "candidate"

    original = "# User configuration\nkey=original\n"

    create_properties(
        before / "config.properties",
        original,
    )

    create_properties(
        after / "config.properties",
        ("key=vendor\nnew.key=new\n"),
    )

    audit = configure_logging(console=False)

    rationalize_properties_directory(
        before,
        after,
        candidate,
        run_id="test-run",
        audit=audit,
    )

    assert (before / "config.properties").read_text(encoding="utf-8") == original


def test_non_properties_files_are_not_processed(tmp_path):
    before = tmp_path / "before"
    after = tmp_path / "after"
    candidate = tmp_path / "candidate"

    before.mkdir(parents=True)
    after.mkdir(parents=True)

    (before / "README.txt").write_text(
        "before\n",
        encoding="utf-8",
    )

    (after / "README.txt").write_text(
        "after\n",
        encoding="utf-8",
    )

    audit = configure_logging(console=False)

    result = rationalize_properties_directory(
        before,
        after,
        candidate,
        run_id="test-run",
        audit=audit,
    )

    assert result.status == "COMPLETED"
    assert result.files == []
