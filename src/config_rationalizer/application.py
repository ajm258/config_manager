import uuid
from pathlib import Path

from ruamel.yaml import YAML

from .core.enums import Format, RunStatus
from .core.exceptions import ConfigurationError
from .core.logging_config import AuditLogger
from .core.models import RunMetadata


class Application:
    """Application orchestration entry point."""

    def __init__(
        self,
        *,
        config_path: Path,
        audit: AuditLogger,
    ) -> None:
        self.config_path = config_path
        self.audit = audit
        self.config = self._load_config()

    def _load_config(self) -> dict:
        if not self.config_path.exists():
            raise ConfigurationError(
                f"Configuration file not found: {self.config_path}"
            )

        yaml = YAML(typ="safe")

        with self.config_path.open("r", encoding="utf-8") as handle:
            data = yaml.load(handle)

        if not isinstance(data, dict):
            raise ConfigurationError(
                "Configuration root must be a mapping."
            )

        return data

    def initialize_run(
        self,
        *,
        profile: str,
        upgrade_id: str,
        target_component: str,
        formats: list[Format],
    ) -> RunMetadata:
        run_id = uuid.uuid4().hex

        source_root = Path(
            self.config["configuration"]["sourceRoot"]
        )

        run_root = (
            Path(self.config["run"]["rootDirectory"]) / run_id
        )

        metadata = RunMetadata(
            run_id=run_id,
            profile=profile,
            upgrade_id=upgrade_id,
            target_component=target_component,
            source_root=source_root,
            run_root=run_root,
            formats=formats,
        )

        self.audit.run_id = run_id
        self.audit.event(
            "RUN_INITIALIZED",
            profile=profile,
            upgrade_id=upgrade_id,
            target_component=target_component,
            formats=[item.value for item in formats],
            source_root=source_root,
            run_root=run_root,
            status=RunStatus.INITIALIZED.value,
        )

        return metadata