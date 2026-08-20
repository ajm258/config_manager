from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from config_rationalizer.core.enums import RunStatus
from config_rationalizer.core.exceptions import ConfigurationError
from config_rationalizer.core.logging_config import AuditLogger
from config_rationalizer.core.models import ChangeRecord
from config_rationalizer.lifecycle.discovery import (
    DiscoveredFile,
    discover_files,
    select_files,
)
from config_rationalizer.lifecycle.handlers import (
    HandlerRegistry,
    build_default_registry,
)
from config_rationalizer.properties.rationalizer import (
    DirectoryRationalizationResult,
    FileRationalizationResult,
    _copy_after_only_file,
    _copy_before_only_file,
    _rationalize_file,
)


@dataclass
class Stage4Run:
    run_id: str
    upgrade_id: str
    profile: str
    target_component: str

    stage0_backup: Path
    after_root: Path
    run_root: Path

    selected_files: list[str] = field(default_factory=list)

    status: RunStatus = RunStatus.INITIALIZED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    errors: list[str] = field(default_factory=list)

    @property
    def before_root(self) -> Path:
        """
        Stage 0 backup is the before configuration.

        No copy is created.
        """
        return self.stage0_backup

    @property
    def candidate_root(self) -> Path:
        return self.run_root / "candidate"

    @property
    def reports_root(self) -> Path:
        return self.run_root / "reports"

    @property
    def logs_root(self) -> Path:
        return self.run_root / "logs"

    def transition(
        self,
        status: RunStatus,
        audit: AuditLogger,
        **details,
    ) -> None:
        previous = self.status

        self.status = status
        self.updated_at = datetime.now(timezone.utc)

        audit.event(
            "RUN_STATUS_CHANGED",
            previous_status=previous.value,
            new_status=status.value,
            **details,
        )


@dataclass
class Stage4Result:
    run: Stage4Run
    files: list[FileRationalizationResult]
    skipped_files: list[str]
    unsupported_files: list[str]
    errors: list[str]
    changes: list[ChangeRecord] = field(default_factory=list)

    @property
    def status(self) -> str:
        return self.run.status.value


def _validate_before(
    root: Path,
    registry: HandlerRegistry,
) -> list[DiscoveredFile]:
    if not root.exists():
        raise ConfigurationError(f"Stage 0 backup does not exist: {root}")

    if not root.is_dir():
        raise ConfigurationError(f"Stage 0 backup is not a directory: {root}")

    files = discover_files(root)

    if not files:
        raise ConfigurationError(f"Stage 0 backup is empty: {root}")

    supported = [item for item in files if registry.get(item.extension) is not None]

    if not supported:
        raise ConfigurationError(
            "Stage 0 backup contains no supported configuration files."
        )

    return files


def _validate_after(root: Path) -> list[DiscoveredFile]:
    if not root.exists():
        raise ConfigurationError(f"After configuration does not exist: {root}")

    if not root.is_dir():
        raise ConfigurationError(f"After configuration is not a directory: {root}")

    return discover_files(root)


def _log_selection(
    *,
    selected: list[DiscoveredFile],
    skipped: list[DiscoveredFile],
    configured_names: list[str],
    audit: AuditLogger,
) -> None:
    audit.event(
        "FILE_SELECTION_COMPLETED",
        configured_files=configured_names,
        selection_mode=("ALL" if not configured_names else "CONFIGURED_LIST"),
        selected_count=len(selected),
        skipped_count=len(skipped),
        selected_files=[str(item.relative_path) for item in selected],
        skipped_files=[str(item.relative_path) for item in skipped],
    )


def run_stage4(
    *,
    run_id: str,
    upgrade_id: str,
    profile: str,
    target_component: str,
    stage0_backup: Path,
    after_root: Path,
    run_root: Path,
    configured_files: list[str],
    audit: AuditLogger,
    registry: HandlerRegistry | None = None,
) -> Stage4Result:
    registry = registry or build_default_registry()
    from config_rationalizer.reporting.report import write_report

    run = Stage4Run(
        run_id=run_id,
        upgrade_id=upgrade_id,
        profile=profile,
        target_component=target_component,
        stage0_backup=stage0_backup.resolve(),
        after_root=after_root.resolve(),
        run_root=run_root.resolve(),
        selected_files=configured_files,
    )

    audit.run_id = run_id

    audit.event(
        "RUN_INITIALIZED",
        upgrade_id=upgrade_id,
        profile=profile,
        target_component=target_component,
        stage0_backup=str(stage0_backup),
        after_root=str(after_root),
        run_root=str(run_root),
    )

    try:
        # ---------------------------------------------------------
        # Stage 0 reference validation
        # ---------------------------------------------------------
        before_files = _validate_before(
            run.before_root,
            registry,
        )

        run.transition(
            RunStatus.BACKUP_REFERENCED,
            audit,
            stage0_backup=str(run.before_root),
        )

        run.transition(
            RunStatus.BEFORE_VALIDATED,
            audit,
            supported_files=len(
                [item for item in before_files if registry.get(item.extension)]
            ),
        )

        # ---------------------------------------------------------
        # After configuration
        # ---------------------------------------------------------
        after_files = _validate_after(
            run.after_root,
        )

        run.transition(
            RunStatus.AFTER_CAPTURED,
            audit,
            files=len(after_files),
        )

        # ---------------------------------------------------------
        # File selection
        # ---------------------------------------------------------
        selected_before, skipped_before = select_files(
            before_files,
            configured_files,
        )

        selected_after, skipped_after = select_files(
            after_files,
            configured_files,
        )

        _log_selection(
            selected=selected_before,
            skipped=skipped_before,
            configured_names=configured_files,
            audit=audit,
        )

        # Use filename selection as the Stage 4 filter, but then
        # match selected files by relative path where possible.
        selected_names = {item.filename for item in selected_before + selected_after}

        before_map = {item.relative_path: item for item in selected_before}

        after_map = {item.relative_path: item for item in selected_after}

        # ---------------------------------------------------------
        # Candidate directory
        # ---------------------------------------------------------
        run.candidate_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        run.reports_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        run.logs_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        results: list[FileRationalizationResult] = []
        errors: list[str] = []

        # ---------------------------------------------------------
        # Process supported files
        # ---------------------------------------------------------
        all_paths = sorted(
            set(before_map) | set(after_map),
            key=str,
        )

        for relative_path in all_paths:
            before_item = before_map.get(relative_path)
            after_item = after_map.get(relative_path)

            # Determine runtime file handler.
            source_item = before_item or after_item

            if source_item is None:
                continue

            handler = registry.get(source_item.extension)

            if handler is None:
                audit.event(
                    "FILE_TYPE_SKIPPED",
                    file=str(relative_path),
                    extension=source_item.extension,
                    reason="No registered handler.",
                )

                continue

            try:
                candidate_path = run.candidate_root / relative_path

                if before_item and not after_item:
                    result = _copy_before_only_file(
                        before_item.path,
                        candidate_path,
                        relative_path,
                        audit,
                    )

                elif after_item and not before_item:
                    result = _copy_after_only_file(
                        after_item.path,
                        candidate_path,
                        relative_path,
                        audit,
                    )

                else:
                    result = handler.rationalize(
                        before_path=before_item.path,
                        after_path=after_item.path,
                        candidate_path=candidate_path,
                        relative_path=relative_path,
                        run_id=run_id,
                        audit=audit,
                    )

                results.append(result)

            except Exception as exc:
                message = f"{relative_path}: {type(exc).__name__}: {exc}"

                errors.append(message)

                audit.event(
                    "FILE_PROCESSING_ERROR",
                    level=40,
                    file=str(relative_path),
                    error=message,
                )

        run.transition(
            RunStatus.COMPARED,
            audit,
            processed_files=len(results),
        )

        run.transition(
            RunStatus.RATIONALIZED,
            audit,
            candidate_root=str(run.candidate_root),
        )

        if errors:
            run.errors.extend(errors)
            run.transition(
                RunStatus.COMPLETED_WITH_ERRORS,
                audit,
                errors=len(errors),
            )
        else:
            run.transition(
                RunStatus.VALIDATED,
                audit,
                candidate_root=str(run.candidate_root),
            )

            run.transition(
                RunStatus.COMPLETED,
                audit,
                candidate_root=str(run.candidate_root),
            )

            result = Stage4Result(
                run=run,
                files=results,
                skipped_files=[
                    str(item.relative_path) for item in skipped_before + skipped_after
                ],
                unsupported_files=[],
                errors=errors,
            )

            changes = [
                change for file_result in result.files for change in file_result.changes
            ]

            report_path = run.reports_root / "report.txt"

            write_report(
                result=result,
                report_path=report_path,
                changes=changes,
            )

            audit.event(
                "RUN_REPORT_GENERATED",
                file=str(report_path),
            )

            return result

    except ConfigurationError as exc:
        message = str(exc)

        run.errors.append(message)

        audit.event(
            "RUN_FAILED",
            level=40,
            error=message,
        )

        run.transition(
            RunStatus.FAILED,
            audit,
            error=message,
        )

        return Stage4Result(
            run=run,
            files=[],
            skipped_files=[],
            unsupported_files=[],
            errors=[message],
        )
