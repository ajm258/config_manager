from pathlib import Path

import pytest

from config_rationalizer.cli import parse_formats
from config_rationalizer.core.enums import (
    Action,
    ChangeType,
    Format,
    RunStatus,
)
from config_rationalizer.core.models import ChangeRecord


def test_parse_formats():
    result = parse_formats("properties,yaml")

    assert result == [
        Format.PROPERTIES,
        Format.YAML,
    ]


def test_unknown_format_is_rejected():
    with pytest.raises(ValueError, match="Unknown format"):
        parse_formats("properties,json")


def test_run_status_is_defined():
    assert RunStatus.INITIALIZED.value == "INITIALIZED"
    assert RunStatus.COMPLETED_WITH_ERRORS.value == (
        "COMPLETED_WITH_ERRORS"
    )


def test_change_record_serialization():
    record = ChangeRecord(
        run_id="run-001",
        component="gateway",
        file="spring-bean.properties",
        format=Format.PROPERTIES,
        logical_path="server.port",
        change_type=ChangeType.VENDOR_VALUE_CHANGED,
        before_value="8080",
        after_value="8081",
        candidate_value="8080",
        action=Action.KEEP_BACKUP,
        review_required=False,
    )

    data = record.to_dict()

    assert data["run_id"] == "run-001"
    assert data["format"] == "properties"
    assert data["change_type"] == "VENDOR_VALUE_CHANGED"
    assert data["action"] == "KEEP_BACKUP"


def test_run_metadata_paths_are_serialized():
    from config_rationalizer.core.models import RunMetadata

    metadata = RunMetadata(
        run_id="run-001",
        profile="test",
        upgrade_id="upgrade-001",
        target_component="gateway",
        source_root=Path("/opt/application/config"),
        run_root=Path("/opt/config-rationalizer/runs/run-001"),
        formats=[Format.PROPERTIES],
    )

    data = metadata.to_dict()

    assert data["run_id"] == "run-001"
    assert data["source_root"] == "/opt/application/config"
    assert data["run_root"] == "/opt/config-rationalizer/runs/run-001"
    assert data["formats"] == ["properties"]
    assert data["status"] == "INITIALIZED"