import json
from pathlib import Path
from typing import Any

from config_rationalizer.properties.comparator import (
    PropertiesComparisonResult,
)
from config_rationalizer.properties.rationalizer import (
    DirectoryRationalizationResult,
)


def comparison_to_dict(
    result: PropertiesComparisonResult,
) -> dict[str, Any]:
    return {
        "status": result.status,
        "before": str(result.before),
        "after": str(result.after),
        "delimiter": result.delimiter,
        "summary": {
            "added": result.added_count,
            "removed_by_vendor": result.removed_count,
            "vendor_value_changed": result.changed_count,
            "unchanged": result.unchanged_count,
            "total": len(result.changes),
        },
        "warnings": result.warnings,
        "errors": result.errors,
        "changes": [change.to_dict() for change in result.changes],
    }


def rationalization_to_dict(
    result: DirectoryRationalizationResult,
) -> dict[str, Any]:
    return {
        "status": result.status,
        "before_root": str(result.before_root),
        "after_root": str(result.after_root),
        "candidate_root": str(result.candidate_root),
        "summary": {
            "files": len(result.files),
            "vendor_added": result.added_count,
            "vendor_removed": result.removed_count,
            "vendor_updated": result.updated_count,
            "unchanged": result.unchanged_count,
        },
        "errors": result.errors,
        "files_detail": [
            {
                "file": str(item.relative_path),
                "status": item.status,
                "vendor_added": item.added,
                "vendor_removed": item.removed,
                "vendor_updated": item.updated,
                "unchanged": item.unchanged,
                "warnings": item.warnings,
                "errors": item.errors,
            }
            for item in result.files
        ],
    }


def write_json_report(
    result: PropertiesComparisonResult,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            comparison_to_dict(result),
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )


def write_rationalization_report(
    result: DirectoryRationalizationResult,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            rationalization_to_dict(result),
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )
