from pathlib import Path

from config_rationalizer.core.enums import Action, ChangeType
from config_rationalizer.core.models import ChangeRecord
from config_rationalizer.lifecycle.run import Stage4Result


def _format_value(value: object) -> str:
    if value is None:
        return ""

    return str(value)


def _file_status(status: str) -> str:
    return status.upper()


def _change_symbol(change_type: ChangeType) -> str:
    if change_type == ChangeType.ADDED:
        return "+"

    if change_type in {
        ChangeType.VENDOR_VALUE_CHANGED,
        ChangeType.TYPE_CHANGED,
        ChangeType.LIST_CHANGED,
        ChangeType.STRUCTURE_CHANGED,
    }:
        return "~"

    if change_type in {
        ChangeType.REMOVED,
        ChangeType.REMOVED_BY_VENDOR,
    }:
        return "-"

    return " "


def _render_change(change: ChangeRecord) -> list[str]:
    lines = []

    symbol = _change_symbol(change.change_type)

    lines.append(f"    {symbol} {change.logical_path or change.file}")

    if change.before_value is not None:
        lines.append(f"        Master:    {change.before_value}")

    if change.after_value is not None:
        lines.append(f"        Vendor:    {change.after_value}")

    if change.candidate_value is not None:
        lines.append(f"        Candidate: {change.candidate_value}")

    if change.action != Action.NONE:
        lines.append(f"        Action:    {change.action.value}")

    if change.review_required:
        lines.append("        Review:    REQUIRED")

    if change.severity.value != "INFORMATIONAL":
        lines.append(f"        Severity:  {change.severity.value}")

    if change.message:
        lines.append(f"        Message:   {change.message}")

    return lines


def render_report(
    *,
    result: Stage4Result,
    changes: list[ChangeRecord] | None = None,
) -> str:
    """
    Render one human-readable report for a Stage 4 run.

    The report is intentionally format-neutral. Properties and XML
    changes are represented through ChangeRecord instances.
    """
    changes = changes or []

    run = result.run

    lines: list[str] = []

    lines.extend(
        [
            "CONFIGURATION RATIONALIZATION REPORT",
            "====================================",
            "",
            f"Run ID:        {run.run_id}",
            f"Upgrade:       {run.upgrade_id}",
            f"Profile:       {run.profile}",
            f"Component:     {run.target_component}",
            f"Status:        {run.status.value}",
            "",
            "SUMMARY",
            "-------",
            f"Files processed: {len(result.files)}",
            f"Files skipped:   {len(result.skipped_files)}",
            f"Errors:          {len(result.errors)}",
            "",
            "FILES",
            "-----",
            "",
        ]
    )

    changes_by_file: dict[str, list[ChangeRecord]] = {}

    for change in changes:
        changes_by_file.setdefault(change.file, []).append(change)

    for file_result in result.files:
        relative_path = str(file_result.relative_path)
        status = _file_status(file_result.status)

        lines.append(f"[{status}] {relative_path}")

        if file_result.added:
            lines.append(f"  Added:    {file_result.added}")

        if file_result.updated:
            lines.append(f"  Updated:  {file_result.updated}")

        if file_result.removed:
            lines.append(f"  Removed:  {file_result.removed}")

        if file_result.unchanged:
            lines.append("  Unchanged: yes")

        file_changes = changes_by_file.get(relative_path, [])

        if file_changes:
            lines.append("")
            lines.append("  Changes:")

            for change in file_changes:
                lines.extend(_render_change(change))

        if file_result.warnings:
            lines.append("")
            lines.append("  Warnings:")

            for warning in file_result.warnings:
                lines.append(f"    - {warning}")

        if file_result.errors:
            lines.append("")
            lines.append("  Errors:")

            for error in file_result.errors:
                lines.append(f"    - {error}")

        lines.append("")

        if result.unsupported_files:
            lines.append("UNSUPPORTED FILES")
            lines.append("-----------------")

            for path in result.unsupported_files:
                lines.append(f"  - {path}")

        lines.append("")

    if result.skipped_files:
        lines.append("SKIPPED FILES")
        lines.append("-------------")

        for path in result.skipped_files:
            lines.append(f"  - {path}")

        lines.append("")

    if result.errors:
        lines.append("RUN ERRORS")
        lines.append("----------")

        for error in result.errors:
            lines.append(f"  - {error}")

        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_report(
    *,
    result: Stage4Result,
    report_path: Path,
    changes: list[ChangeRecord] | None = None,
) -> Path:
    """Render and write the central human-readable run report."""
    report_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path.write_text(
        render_report(
            result=result,
            changes=changes,
        ),
        encoding="utf-8",
    )

    return report_path
