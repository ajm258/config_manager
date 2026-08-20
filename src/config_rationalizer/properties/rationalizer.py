from dataclasses import dataclass, field
from pathlib import Path
from shutil import copy2

from config_rationalizer.core.enums import ChangeType
from config_rationalizer.core.logging_config import AuditLogger
from config_rationalizer.core.models import ChangeRecord

from .comparator import PropertiesComparisonResult, compare_properties
from .parser import PropertyEntry, parse_properties

GENERATED_MARKER = (
    "# ============================================================\n"
    "# CONFIGURATION RATIONALIZER - VENDOR ADDED PROPERTIES\n"
    "# ============================================================"
)


@dataclass
class FileRationalizationResult:
    relative_path: Path
    status: str
    added: int = 0
    removed: int = 0
    updated: int = 0
    unchanged: int = 0
    changes: list[ChangeRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class DirectoryRationalizationResult:
    before_root: Path
    after_root: Path
    candidate_root: Path
    status: str
    files: list[FileRationalizationResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def added_count(self) -> int:
        return sum(file.added for file in self.files)

    @property
    def removed_count(self) -> int:
        return sum(file.removed for file in self.files)

    @property
    def updated_count(self) -> int:
        return sum(file.updated for file in self.files)

    @property
    def unchanged_count(self) -> int:
        return sum(file.unchanged for file in self.files)


def _properties_files(root: Path) -> set[Path]:
    return {
        path.relative_to(root) for path in root.rglob("*.properties") if path.is_file()
    }


def _read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


def _line_ending(line: str) -> str:
    if line.endswith("\r\n"):
        return "\r\n"

    if line.endswith("\n"):
        return "\n"

    return ""


def _render_property(
    entry: PropertyEntry,
    delimiter: str,
) -> str:
    return f"{entry.key}{delimiter}{entry.value}\n"


def _append_vendor_properties(
    lines: list[str],
    *,
    entries: list[PropertyEntry],
    delimiter: str,
) -> list[str]:
    if not entries:
        return lines

    output = list(lines)

    if output and not output[-1].endswith(("\n", "\r\n")):
        output[-1] += "\n"

    if output and output[-1].strip():
        output.append("\n")

    output.append(GENERATED_MARKER + "\n")

    for entry in entries:
        output.append(
            _render_property(
                entry,
                delimiter,
            )
        )

    return output


def _rationalize_file(
    *,
    before_path: Path,
    after_path: Path,
    candidate_path: Path,
    relative_path: Path,
    run_id: str,
    audit: AuditLogger,
) -> FileRationalizationResult:
    comparison = compare_properties(
        before_path,
        after_path,
        run_id=run_id,
        audit=audit,
    )

    if comparison.status != "COMPLETED":
        return FileRationalizationResult(
            relative_path=relative_path,
            status=comparison.status,
            warnings=comparison.warnings,
            errors=comparison.errors,
        )

    before = parse_properties(before_path)
    after = parse_properties(after_path)

    candidate_lines = _read_lines(before_path)

    added_keys = {
        change.logical_path
        for change in comparison.changes
        if change.change_type == ChangeType.ADDED
    }

    additions = [entry for key, entry in after.entries.items() if key in added_keys]

    candidate_lines = _append_vendor_properties(
        candidate_lines,
        entries=additions,
        delimiter=before.delimiter,
    )

    candidate_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    candidate_path.write_text(
        "".join(candidate_lines),
        encoding="utf-8",
    )

    unchanged = comparison.unchanged_count

    audit.event(
        "PROPERTIES_FILE_RATIONALIZED",
        file=str(relative_path),
        status="COMPLETED",
        added=len(additions),
        removed=comparison.removed_count,
        updated=comparison.changed_count,
        unchanged=unchanged,
    )

    return FileRationalizationResult(
        relative_path=relative_path,
        status="COMPLETED",
        added=len(additions),
        removed=comparison.removed_count,
        updated=comparison.changed_count,
        unchanged=unchanged,
        changes=comparison.changes,
    )


def _copy_before_only_file(
    before_path: Path,
    candidate_path: Path,
    relative_path: Path,
    audit: AuditLogger,
) -> FileRationalizationResult:
    candidate_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    copy2(
        before_path,
        candidate_path,
    )

    audit.event(
        "BEFORE_ONLY_FILE_RETAINED",
        file=str(relative_path),
        reason="Before configuration is authoritative.",
    )

    return FileRationalizationResult(
        relative_path=relative_path,
        status="RETAINED",
    )


def _copy_after_only_file(
    after_path: Path,
    candidate_path: Path,
    relative_path: Path,
    audit: AuditLogger,
) -> FileRationalizationResult:
    candidate_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    copy2(
        after_path,
        candidate_path,
    )

    audit.event(
        "AFTER_ONLY_FILE_ADDED",
        file=str(relative_path),
        reason="Vendor supplied a new configuration file.",
    )

    return FileRationalizationResult(
        relative_path=relative_path,
        status="ADDED",
    )


def rationalize_properties_directory(
    before_root: Path,
    after_root: Path,
    candidate_root: Path,
    *,
    run_id: str,
    audit: AuditLogger,
) -> DirectoryRationalizationResult:
    """
    Recursively rationalize all .properties files.

    The before directory is authoritative and neither source directory
    is modified.
    """
    before_root = before_root.resolve()
    after_root = after_root.resolve()
    candidate_root = candidate_root.resolve()

    audit.event(
        "PROPERTIES_DIRECTORY_RATIONALIZATION_STARTED",
        before_root=str(before_root),
        after_root=str(after_root),
        candidate_root=str(candidate_root),
    )

    before_files = _properties_files(before_root)
    after_files = _properties_files(after_root)

    all_files = sorted(
        before_files | after_files,
        key=lambda path: str(path),
    )

    result = DirectoryRationalizationResult(
        before_root=before_root,
        after_root=after_root,
        candidate_root=candidate_root,
        status="COMPLETED",
    )

    for relative_path in all_files:
        before_path = before_root / relative_path
        after_path = after_root / relative_path
        candidate_path = candidate_root / relative_path

        try:
            if relative_path in before_files and relative_path not in after_files:
                file_result = _copy_before_only_file(
                    before_path,
                    candidate_path,
                    relative_path,
                    audit,
                )

            elif relative_path not in before_files and relative_path in after_files:
                file_result = _copy_after_only_file(
                    after_path,
                    candidate_path,
                    relative_path,
                    audit,
                )

            else:
                file_result = _rationalize_file(
                    before_path=before_path,
                    after_path=after_path,
                    candidate_path=candidate_path,
                    relative_path=relative_path,
                    run_id=run_id,
                    audit=audit,
                )

            result.files.append(file_result)

        except Exception as exc:
            message = (
                f"Failed to rationalize {relative_path}: {type(exc).__name__}: {exc}"
            )

            audit.event(
                "PROPERTIES_FILE_RATIONALIZATION_ERROR",
                level=40,
                file=str(relative_path),
                error=message,
            )

            result.files.append(
                FileRationalizationResult(
                    relative_path=relative_path,
                    status="ERROR",
                    errors=[message],
                )
            )

            result.errors.append(message)

    if result.errors:
        result.status = "COMPLETED_WITH_ERRORS"

    audit.event(
        "PROPERTIES_DIRECTORY_RATIONALIZATION_COMPLETED",
        status=result.status,
        files=len(result.files),
        added=result.added_count,
        removed=result.removed_count,
        updated=result.updated_count,
        unchanged=result.unchanged_count,
    )

    return result
