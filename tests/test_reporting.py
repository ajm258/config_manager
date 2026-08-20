from pathlib import Path

import pytest

from config_rationalizer.core.enums import (
    Action,
    ChangeType,
    Format,
    RunStatus,
)
from config_rationalizer.core.models import ChangeRecord
from config_rationalizer.lifecycle.run import (
    Stage4Result,
    Stage4Run,
)
from config_rationalizer.properties.rationalizer import (
    FileRationalizationResult,
)
from config_rationalizer.reporting.report import render_report


@pytest.fixture
def stage4_result(tmp_path):
    run = Stage4Run(
        run_id="run-001",
        upgrade_id="upgrade-001",
        profile="test",
        target_component="gateway",
        stage0_backup=tmp_path / "before",
        after_root=tmp_path / "after",
        run_root=tmp_path / "run",
    )

    run.status = RunStatus.COMPLETED

    file_result = FileRationalizationResult(
        relative_path=Path("config/application.properties"),
        status="COMPLETED",
        added=1,
        removed=0,
        updated=2,
        unchanged=0,
    )

    return Stage4Result(
        run=run,
        files=[file_result],
        skipped_files=[],
        unsupported_files=[],
        errors=[],
    )


def test_report_contains_run_information(stage4_result):
    report = render_report(result=stage4_result)

    assert "CONFIGURATION RATIONALIZATION REPORT" in report
    assert stage4_result.run.run_id in report
    assert stage4_result.run.upgrade_id in report
    assert stage4_result.run.profile in report
    assert stage4_result.run.target_component in report


def test_report_contains_file_result(stage4_result):
    report = render_report(result=stage4_result)

    file_result = stage4_result.files[0]

    assert str(file_result.relative_path) in report
    assert file_result.status in report
    assert "Added:    1" in report
    assert "Updated:  2" in report


def test_report_contains_change_details(stage4_result):
    change = ChangeRecord(
        run_id=stage4_result.run.run_id,
        component=stage4_result.run.target_component,
        file="config/application.properties",
        format=Format.PROPERTIES,
        logical_path="server.port",
        change_type=ChangeType.VENDOR_VALUE_CHANGED,
        before_value="8080",
        after_value="9090",
        candidate_value="8080",
        action=Action.KEEP_BACKUP,
    )

    report = render_report(
        result=stage4_result,
        changes=[change],
    )

    assert "server.port" in report
    assert "Master:    8080" in report
    assert "Vendor:    9090" in report
    assert "Candidate: 8080" in report
    assert "KEEP_BACKUP" in report


def test_report_contains_skipped_files(stage4_result):
    stage4_result.skipped_files.append("config/legacy.xml")

    report = render_report(result=stage4_result)

    assert "SKIPPED FILES" in report
    assert "config/legacy.xml" in report


def test_report_contains_errors(stage4_result):
    stage4_result.errors.append("config/broken.xml: parse failure")

    report = render_report(result=stage4_result)

    assert "RUN ERRORS" in report
    assert "config/broken.xml: parse failure" in report
