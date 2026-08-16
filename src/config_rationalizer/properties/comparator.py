from dataclasses import dataclass
from pathlib import Path

from config_rationalizer.core.enums import (
    Action,
    ChangeType,
    Format,
    Severity,
)
from config_rationalizer.core.logging_config import AuditLogger
from config_rationalizer.core.models import ChangeRecord

from .parser import ParsedProperties, PropertiesParseError, parse_properties


@dataclass
class PropertiesComparisonResult:
    before: Path
    after: Path
    status: str
    delimiter: str | None
    changes: list[ChangeRecord]
    warnings: list[str]
    errors: list[str]

    @property
    def added_count(self) -> int:
        return sum(item.change_type == ChangeType.ADDED for item in self.changes)

    @property
    def removed_count(self) -> int:
        return sum(
            item.change_type == ChangeType.REMOVED_BY_VENDOR for item in self.changes
        )

    @property
    def changed_count(self) -> int:
        return sum(
            item.change_type == ChangeType.VENDOR_VALUE_CHANGED for item in self.changes
        )

    @property
    def unchanged_count(self) -> int:
        return sum(item.change_type == ChangeType.UNCHANGED for item in self.changes)


def _build_change(
    *,
    run_id: str,
    key: str,
    before: str | None,
    after: str | None,
    change_type: ChangeType,
    action: Action,
    severity: Severity,
    message: str,
) -> ChangeRecord:
    return ChangeRecord(
        run_id=run_id,
        component=None,
        file="",
        format=Format.PROPERTIES,
        logical_path=key,
        change_type=change_type,
        before_value=before,
        after_value=after,
        candidate_value=None,
        action=action,
        review_required=False,
        severity=severity,
        message=message,
    )


def _compare_entries(
    *,
    run_id: str,
    before: ParsedProperties,
    after: ParsedProperties,
) -> list[ChangeRecord]:
    changes: list[ChangeRecord] = []

    all_keys = sorted(set(before.entries) | set(after.entries))

    for key in all_keys:
        before_entry = before.entries.get(key)
        after_entry = after.entries.get(key)

        before_value = before_entry.value if before_entry is not None else None

        after_value = after_entry.value if after_entry is not None else None

        if before_entry is None:
            changes.append(
                _build_change(
                    run_id=run_id,
                    key=key,
                    before=None,
                    after=after_value,
                    change_type=ChangeType.ADDED,
                    action=Action.ADD_VENDOR_DEFAULT,
                    severity=Severity.INFORMATIONAL,
                    message="Property exists only in after configuration.",
                )
            )
            continue

        if after_entry is None:
            changes.append(
                _build_change(
                    run_id=run_id,
                    key=key,
                    before=before_value,
                    after=None,
                    change_type=ChangeType.REMOVED_BY_VENDOR,
                    action=Action.KEEP_BACKUP,
                    severity=Severity.MEDIUM,
                    message=(
                        "Property existed before but is absent from "
                        "after configuration."
                    ),
                )
            )
            continue

        if before_value == after_value:
            changes.append(
                _build_change(
                    run_id=run_id,
                    key=key,
                    before=before_value,
                    after=after_value,
                    change_type=ChangeType.UNCHANGED,
                    action=Action.NONE,
                    severity=Severity.INFORMATIONAL,
                    message="Property value is unchanged.",
                )
            )
            continue

        changes.append(
            _build_change(
                run_id=run_id,
                key=key,
                before=before_value,
                after=after_value,
                change_type=ChangeType.VENDOR_VALUE_CHANGED,
                action=Action.KEEP_BACKUP,
                severity=Severity.MEDIUM,
                message=(
                    "Vendor changed an existing property value; "
                    "before value remains authoritative."
                ),
            )
        )

    return changes


def compare_properties(
    before_path: Path,
    after_path: Path,
    *,
    run_id: str,
    audit: AuditLogger,
) -> PropertiesComparisonResult:
    audit.event(
        "PROPERTIES_COMPARISON_STARTED",
        before=str(before_path),
        after=str(after_path),
    )

    warnings: list[str] = []
    errors: list[str] = []

    try:
        before = parse_properties(before_path)
    except PropertiesParseError as exc:
        message = str(exc)

        if "No properties delimiter found" in message:
            warnings.append(message)

            audit.event(
                "PROPERTIES_FILE_SKIPPED",
                level=30,
                file=str(before_path),
                reason=message,
            )

            return PropertiesComparisonResult(
                before=before_path,
                after=after_path,
                status="SKIPPED",
                delimiter=None,
                changes=[],
                warnings=warnings,
                errors=[],
            )

        errors.append(message)

        audit.event(
            "PROPERTIES_COMPARISON_ERROR",
            level=40,
            file=str(before_path),
            error=message,
        )

        return PropertiesComparisonResult(
            before=before_path,
            after=after_path,
            status="ERROR",
            delimiter=None,
            changes=[],
            warnings=[],
            errors=errors,
        )

    try:
        after = parse_properties(after_path)
    except PropertiesParseError as exc:
        message = str(exc)

        if "No properties delimiter found" in message:
            warnings.append(message)

            audit.event(
                "PROPERTIES_FILE_SKIPPED",
                level=30,
                file=str(after_path),
                reason=message,
            )

            return PropertiesComparisonResult(
                before=before_path,
                after=after_path,
                status="SKIPPED",
                delimiter=None,
                changes=[],
                warnings=warnings,
                errors=[],
            )

        errors.append(message)

        audit.event(
            "PROPERTIES_COMPARISON_ERROR",
            level=40,
            file=str(after_path),
            error=message,
        )

        return PropertiesComparisonResult(
            before=before_path,
            after=after_path,
            status="ERROR",
            delimiter=None,
            changes=[],
            warnings=[],
            errors=errors,
        )

    if before.delimiter != after.delimiter:
        message = (
            "Deployment/configuration inconsistency: before file uses "
            f"{before.delimiter!r} delimiter while after file uses "
            f"{after.delimiter!r}."
        )

        errors.append(message)

        audit.event(
            "PROPERTIES_DELIMITER_MISMATCH",
            level=40,
            before=str(before_path),
            after=str(after_path),
            before_delimiter=before.delimiter,
            after_delimiter=after.delimiter,
            error=message,
        )

        return PropertiesComparisonResult(
            before=before_path,
            after=after_path,
            status="ERROR",
            delimiter=None,
            changes=[],
            warnings=[],
            errors=errors,
        )

    changes = _compare_entries(
        run_id=run_id,
        before=before,
        after=after,
    )

    for change in changes:
        change.file = str(before_path)

    audit.event(
        "PROPERTIES_COMPARISON_COMPLETED",
        before=str(before_path),
        after=str(after_path),
        delimiter=before.delimiter,
        total_changes=len(changes),
        added=sum(c.change_type == ChangeType.ADDED for c in changes),
        removed=sum(c.change_type == ChangeType.REMOVED_BY_VENDOR for c in changes),
        changed=sum(c.change_type == ChangeType.VENDOR_VALUE_CHANGED for c in changes),
        unchanged=sum(c.change_type == ChangeType.UNCHANGED for c in changes),
    )

    return PropertiesComparisonResult(
        before=before_path,
        after=after_path,
        status="COMPLETED",
        delimiter=before.delimiter,
        changes=changes,
        warnings=warnings,
        errors=errors,
    )
