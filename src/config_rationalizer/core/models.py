from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .enums import (
    Action,
    ChangeType,
    Format,
    ModuleStatus,
    Ownership,
    RunStatus,
    Severity,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class RunMetadata:
    run_id: str
    profile: str
    upgrade_id: str
    target_component: str
    source_root: Path
    run_root: Path
    formats: list[Format]
    status: RunStatus = RunStatus.INITIALIZED
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["source_root"] = str(self.source_root)
        data["run_root"] = str(self.run_root)
        data["formats"] = [item.value for item in self.formats]
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        return data


@dataclass
class FileRecord:
    path: str
    format: Format | None = None
    component: str | None = None
    ownership: Ownership = Ownership.UNKNOWN
    size: int | None = None
    checksum: str | None = None


@dataclass
class ChangeRecord:
    run_id: str
    component: str | None
    file: str
    format: Format
    logical_path: str | None
    change_type: ChangeType
    before_value: Any = None
    after_value: Any = None
    candidate_value: Any = None
    action: Action = Action.NONE
    review_required: bool = False
    severity: Severity = Severity.INFORMATIONAL
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)

        for field_name in (
            "format",
            "change_type",
            "action",
            "severity",
        ):
            value = data[field_name]
            data[field_name] = value.value

        return data


@dataclass
class ModuleResult:
    format: Format
    status: ModuleStatus
    processed_files: int = 0
    failed_files: int = 0
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": self.format.value,
            "status": self.status.value,
            "processed_files": self.processed_files,
            "failed_files": self.failed_files,
            "message": self.message,
        }


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }