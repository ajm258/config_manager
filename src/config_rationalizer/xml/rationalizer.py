from pathlib import Path
from shutil import copy2

from lxml import etree

from config_rationalizer.core.logging_config import AuditLogger
from config_rationalizer.properties.rationalizer import FileRationalizationResult

from .comparator import (
    _build_element_map,
    compare_xml_files,
)
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

    candidate_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Preserve the master file exactly when there are no changes.
    copy2(
        before_path,
        candidate_path,
    )

    if comparison.changes:
        before_tree = etree.parse(
            str(before_path),
            etree.XMLParser(
                remove_blank_text=False,
                resolve_entities=False,
                no_network=True,
            ),
        )

        after_tree = etree.parse(
            str(after_path),
            etree.XMLParser(
                remove_blank_text=False,
                resolve_entities=False,
                no_network=True,
            ),
        )

        _apply_xml_changes(
            candidate_tree=before_tree,
            before_tree=before_tree,
            after_tree=after_tree,
            comparison=comparison,
        )

        before_tree.write(
            str(candidate_path),
            encoding="UTF-8",
            xml_declaration=True,
            pretty_print=True,
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
        changes=comparison.changes,
    )


def _apply_xml_changes(
    *,
    candidate_tree: etree._ElementTree,
    before_tree: etree._ElementTree,
    after_tree: etree._ElementTree,
    comparison,
) -> None:
    before_map = _build_element_map(
        before_tree.getroot(),
    )

    after_map = _build_element_map(
        after_tree.getroot(),
    )

    for change in comparison.changes:
        candidate_map = _build_element_map(
            candidate_tree.getroot(),
        )

        if change.change_type == XmlChangeType.ADDED:
            after_element = after_map.get(change.path)

            if after_element is None:
                continue

            parent_path = change.path.rsplit("/", 1)[0]

            parent = candidate_map.get(parent_path)

            if parent is None:
                continue

            parent.append(
                etree.fromstring(
                    etree.tostring(after_element),
                )
            )

        elif change.change_type == XmlChangeType.REMOVED:
            candidate_element = candidate_map.get(change.path)

            if candidate_element is None:
                continue

            parent = candidate_element.getparent()

            if parent is not None:
                parent.remove(candidate_element)

        elif change.change_type == XmlChangeType.VALUE_CHANGED:
            candidate_element = candidate_map.get(change.path)

            if candidate_element is not None:
                candidate_element.text = change.before_value

        elif change.change_type == XmlChangeType.ATTRIBUTE_CHANGED:
            candidate_element = candidate_map.get(change.path)

            if candidate_element is None or change.attribute is None:
                continue

            if change.before_value is None and change.after_value is not None:
                # Attribute was added by vendor.
                candidate_element.set(
                    change.attribute,
                    change.after_value,
                )

            elif change.before_value is not None and change.after_value is None:
                # Attribute was removed by vendor.
                candidate_element.attrib.pop(
                    change.attribute,
                    None,
                )

            else:
                # Attribute value changed.
                candidate_element.set(
                    change.attribute,
                    change.before_value,
                )
