from pathlib import Path

from lxml import etree

from config_rationalizer.core.logging_config import configure_logging
from config_rationalizer.lifecycle.handlers import build_default_registry
from config_rationalizer.xml.rationalizer import _rationalize_file


def write_xml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_xml_handler_is_registered():
    registry = build_default_registry()

    handler = registry.get(".xml")

    assert handler is not None
    assert handler.name == "xml"


def test_xml_same_schema_version_is_processed(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"
    candidate = tmp_path / "candidate.xml"

    content_before = """<?xml version="1.0" encoding="UTF-8"?>
<configuration
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://example.com/config example-config-1.0.xsd">
    <server>
        <port>8080</port>
    </server>
</configuration>
"""

    content_after = """<?xml version="1.0" encoding="UTF-8"?>
<configuration
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://example.com/config example-config-1.0.xsd">
    <server>
        <port>9090</port>
    </server>
</configuration>
"""

    write_xml(before, content_before)
    write_xml(after, content_after)

    audit = configure_logging(console=False)

    result = _rationalize_file(
        before_path=before,
        after_path=after,
        candidate_path=candidate,
        relative_path=Path("config.xml"),
        run_id="test-run",
        audit=audit,
    )

    assert result.status == "COMPLETED"
    assert result.updated == 1
    assert result.added == 0
    assert result.removed == 0
    assert candidate.exists()

    candidate_tree = etree.parse(str(candidate))

    port = candidate_tree.find("./server/port")

    assert port is not None
    assert port.text == "8080"


def test_xml_without_schema_is_processed(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"
    candidate = tmp_path / "candidate.xml"

    write_xml(
        before,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <server>
        <port>8080</port>
    </server>
</configuration>
""",
    )

    write_xml(
        after,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <server>
        <port>9090</port>
    </server>
</configuration>
""",
    )

    audit = configure_logging(console=False)

    result = _rationalize_file(
        before_path=before,
        after_path=after,
        candidate_path=candidate,
        relative_path=Path("config.xml"),
        run_id="test-run",
        audit=audit,
    )

    assert result.status == "COMPLETED"
    assert result.updated == 1
    assert result.added == 0
    assert result.removed == 0
    assert candidate.exists()

    candidate_tree = etree.parse(str(candidate))

    port = candidate_tree.find("./server/port")

    assert port is not None
    assert port.text == "8080"


def test_xml_schema_version_mismatch_is_skipped(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"
    candidate = tmp_path / "candidate.xml"

    write_xml(
        before,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://example.com/config example-config-1.0.xsd">
</configuration>
""",
    )

    write_xml(
        after,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://example.com/config example-config-1.1.xsd">
</configuration>
""",
    )

    audit = configure_logging(console=False)

    result = _rationalize_file(
        before_path=before,
        after_path=after,
        candidate_path=candidate,
        relative_path=Path("config.xml"),
        run_id="test-run",
        audit=audit,
    )

    assert result.status == "SKIPPED"
    assert result.warnings
    assert not candidate.exists()


def test_xml_schema_version_missing_on_one_side_is_skipped(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"
    candidate = tmp_path / "candidate.xml"

    write_xml(
        before,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
</configuration>
""",
    )

    write_xml(
        after,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://example.com/config example-config-1.0.xsd">
</configuration>
""",
    )

    audit = configure_logging(console=False)

    result = _rationalize_file(
        before_path=before,
        after_path=after,
        candidate_path=candidate,
        relative_path=Path("config.xml"),
        run_id="test-run",
        audit=audit,
    )

    assert result.status == "SKIPPED"
    assert result.warnings
    assert not candidate.exists()


def test_xml_added_removed_and_updated_changes_are_counted(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"
    candidate = tmp_path / "candidate.xml"

    write_xml(
        before,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <server>
        <port>8080</port>
        <host>localhost</host>
    </server>
</configuration>
""",
    )

    write_xml(
        after,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <server>
        <port>9090</port>
        <protocol>https</protocol>
    </server>
</configuration>
""",
    )

    audit = configure_logging(console=False)

    result = _rationalize_file(
        before_path=before,
        after_path=after,
        candidate_path=candidate,
        relative_path=Path("config.xml"),
        run_id="test-run",
        audit=audit,
    )

    assert result.status == "COMPLETED"
    assert result.updated == 1
    assert result.added == 1
    assert result.removed == 1
    assert candidate.exists()

    candidate_tree = etree.parse(str(candidate))

    port = candidate_tree.find("./server/port")
    host = candidate_tree.find("./server/host")
    protocol = candidate_tree.find("./server/protocol")

    # Vendor changed the value, so revert to master.
    assert port is not None
    assert port.text == "8080"

    # Vendor removed the node, so it remains removed.
    assert host is None

    # Vendor added the node, so it is retained.
    assert protocol is not None
    assert protocol.text == "https"
