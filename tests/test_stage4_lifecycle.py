from pathlib import Path

from config_rationalizer.core.enums import RunStatus
from config_rationalizer.core.logging_config import configure_logging
from config_rationalizer.lifecycle.discovery import (
    discover_files,
    select_files,
)
from config_rationalizer.lifecycle.run import run_stage4


def write(path: Path, content: str) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        content,
        encoding="utf-8",
    )


def test_recursive_discovery(tmp_path):
    root = tmp_path / "config"

    write(
        root / "a" / "spring-beans.properties",
        "a=value\n",
    )

    write(
        root / "b" / "nested" / "application.properties",
        "b=value\n",
    )

    files = discover_files(root)

    assert len(files) == 2

    names = {item.filename for item in files}

    assert names == {
        "spring-beans.properties",
        "application.properties",
    }


def test_empty_selection_list_selects_all(tmp_path):
    root = tmp_path / "config"

    write(
        root / "a.properties",
        "a=value\n",
    )

    write(
        root / "b.properties",
        "b=value\n",
    )

    files = discover_files(root)

    selected, skipped = select_files(
        files,
        [],
    )

    assert len(selected) == 2
    assert skipped == []


def test_configured_selection_matches_filename_only(tmp_path):
    root = tmp_path / "config"

    write(
        root / "one" / "spring-beans.properties",
        "one=value\n",
    )

    write(
        root / "two" / "spring-beans.properties",
        "two=value\n",
    )

    write(
        root / "three" / "other.properties",
        "three=value\n",
    )

    files = discover_files(root)

    selected, skipped = select_files(
        files,
        ["spring-beans.properties"],
    )

    assert len(selected) == 2
    assert all(item.filename == "spring-beans.properties" for item in selected)

    assert len(skipped) == 1


def test_missing_stage0_backup_fails(tmp_path):
    audit = configure_logging(console=False)

    result = run_stage4(
        run_id="run-001",
        upgrade_id="upgrade-001",
        profile="test",
        target_component="gateway",
        stage0_backup=tmp_path / "missing",
        after_root=tmp_path / "after",
        run_root=tmp_path / "run",
        configured_files=[],
        audit=audit,
    )

    assert result.status == RunStatus.FAILED.value
    assert result.errors


def test_empty_stage0_backup_fails(tmp_path):
    before = tmp_path / "before"
    after = tmp_path / "after"

    before.mkdir()
    after.mkdir()

    audit = configure_logging(console=False)

    result = run_stage4(
        run_id="run-001",
        upgrade_id="upgrade-001",
        profile="test",
        target_component="gateway",
        stage0_backup=before,
        after_root=after,
        run_root=tmp_path / "run",
        configured_files=[],
        audit=audit,
    )

    assert result.status == RunStatus.FAILED.value
    assert "empty" in result.errors[0].lower()


def test_stage0_backup_is_used_directly(tmp_path):
    before = tmp_path / "before"
    after = tmp_path / "after"
    run_root = tmp_path / "run"

    write(
        before / "spring-beans.properties",
        "key=user-value\n",
    )

    write(
        after / "spring-beans.properties",
        "key=vendor-value\nnew=value\n",
    )

    audit = configure_logging(console=False)

    result = run_stage4(
        run_id="run-001",
        upgrade_id="upgrade-001",
        profile="test",
        target_component="gateway",
        stage0_backup=before,
        after_root=after,
        run_root=run_root,
        configured_files=[],
        audit=audit,
    )

    assert result.status == RunStatus.COMPLETED.value

    candidate = run_root / "candidate" / "spring-beans.properties"

    assert candidate.exists()

    assert candidate.read_text(encoding="utf-8").startswith("key=user-value")


def test_configured_filename_filters_files(tmp_path):
    before = tmp_path / "before"
    after = tmp_path / "after"
    run_root = tmp_path / "run"

    write(
        before / "spring-beans.properties",
        "key=before\n",
    )

    write(
        before / "ignored.properties",
        "ignored=before\n",
    )

    write(
        after / "spring-beans.properties",
        "key=after\n",
    )

    write(
        after / "ignored.properties",
        "ignored=after\n",
    )

    audit = configure_logging(console=False)

    result = run_stage4(
        run_id="run-001",
        upgrade_id="upgrade-001",
        profile="test",
        target_component="gateway",
        stage0_backup=before,
        after_root=after,
        run_root=run_root,
        configured_files=[
            "spring-beans.properties",
        ],
        audit=audit,
    )

    assert result.status == RunStatus.COMPLETED.value

    assert (run_root / "candidate" / "spring-beans.properties").exists()

    assert not (run_root / "candidate" / "ignored.properties").exists()
