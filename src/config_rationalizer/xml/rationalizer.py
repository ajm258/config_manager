from pathlib import Path
from shutil import copy2

from config_rationalizer.core.logging_config import AuditLogger
from config_rationalizer.properties.rationalizer import FileRationalizationResult

from .comparator import compare_xml_files
from .models import XmlChangeType, XmlSchemaStatus


def _rationalize_file(
    *,
    before_path: Path,
    after_path: Path,
    candidate_path: Path,
    relative_path: Path,
    run_id: str,
    audit: AuditLogger,
) -> FileRationalizationResult:
    try:
        comparison = compare_xml_files(
            before_path,
            after_path,
        )

    except Exception as exc:
        message = f"Failed to compare XML {relative_path}: {type(exc).__name__}: {exc}"

        audit.event(
            "XML_FILE_COMPARISON_ERROR",
            level=40,
            file=str(relative_path),
            error=message,
        )

        return FileRationalizationResult(
            relative_path=relative_path,
            status="ERROR",
            errors=[message],
        )

    if comparison.schema_status == XmlSchemaStatus.VERSION_CHANGED:
        message = (
            f"Skipped XML comparison for {relative_path}: "
            f"current schema {comparison.before_schema.version} and "
            f"new schema {comparison.after_schema.version} are different. "
            "The file requires manual review."
        )

    elif comparison.schema_status == XmlSchemaStatus.UNKNOWN_SCHEMA:
        message = (
            f"Skipped XML comparison for {relative_path}: "
            "schema identity could not be determined reliably. "
            "The file requires manual review."
        )

    elif comparison.schema_status == XmlSchemaStatus.VERSION_MISSING_ON_ONE_SIDE:
        message = (
            f"Skipped XML comparison for {relative_path}: "
            "schema is present on only one side. "
            "The file requires manual review."
        )

    else:
        message = None

    if message is not None:
        audit.event(
            "XML_FILE_COMPARISON_SKIPPED",
            level=30,
            file=str(relative_path),
            schema_status=comparison.schema_status.value,
            reason=message,
        )

        return FileRationalizationResult(
            relative_path=relative_path,
            status="SKIPPED",
            warnings=[message],
        )

    added = 0
    removed = 0
    updated = 0

    for change in comparison.changes:
        if change.change_type == XmlChangeType.ADDED:
            added += 1

        elif change.change_type == XmlChangeType.REMOVED:
            removed += 1

        else:
            updated += 1

        audit.event(
            "XML_CHANGE_DETECTED",
            file=str(relative_path),
            change_type=change.change_type.value,
            logical_path=change.path,
            attribute=change.attribute,
            before_value=change.before_value,
            after_value=change.after_value,
        )

    # Stage 6 does comparison only.
    # The before configuration remains authoritative until XML
    # rationalization rules are explicitly introduced.
    candidate_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    copy2(
        before_path,
        candidate_path,
    )

    unchanged = 1 if not comparison.changes else 0

    audit.event(
        "XML_FILE_COMPARED",
        file=str(relative_path),
        status="COMPLETED",
        schema_status=comparison.schema_status.value,
        added=added,
        removed=removed,
        updated=updated,
        unchanged=unchanged,
    )

    return FileRationalizationResult(
        relative_path=relative_path,
        status="COMPLETED",
        added=added,
        removed=removed,
        updated=updated,
        unchanged=unchanged,
    )
