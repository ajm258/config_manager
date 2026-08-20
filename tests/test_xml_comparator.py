from pathlib import Path

from config_rationalizer.xml.comparator import compare_xml_files
from config_rationalizer.xml.models import XmlSchemaStatus
import pytest


def write_xml(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_same_schema_version_is_comparable(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    write_xml(
        before,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://example.com/config example-config-1.0.xsd">
    <property name="TRACE_PATH" value="/old/path"/>
</configuration>
""",
    )

    write_xml(
        after,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://example.com/config example-config-1.0.xsd">
    <property name="TRACE_PATH" value="/new/path"/>
</configuration>
""",
    )

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.VERSION_MATCH


def test_different_schema_version_is_skipped(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

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

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.VERSION_CHANGED
    assert result.changes == []


def test_no_schema_version_on_either_side_is_comparable(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    write_xml(
        before,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <property name="TRACE_PATH" value="/old/path"/>
</configuration>
""",
    )

    write_xml(
        after,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <property name="TRACE_PATH" value="/new/path"/>
</configuration>
""",
    )

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.NO_VERSION
    assert len(result.changes) > 0


def test_schema_version_missing_on_one_side_is_skipped(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    write_xml(
        before,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <property name="TRACE_PATH" value="/old/path"/>
</configuration>
""",
    )

    write_xml(
        after,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://example.com/config example-config-1.0.xsd">
    <property name="TRACE_PATH" value="/new/path"/>
</configuration>
""",
    )

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.VERSION_MISSING_ON_ONE_SIDE
    assert result.changes == []


def test_element_value_change_is_detected(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

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

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.NO_VERSION
    assert len(result.changes) == 1

    change = result.changes[0]

    assert change.change_type.value == "VALUE_CHANGED"
    assert change.before_value == "8080"
    assert change.after_value == "9090"


def test_repeated_elements_are_distinguished_by_name_attribute(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    write_xml(
        before,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <property name="TRACE_PATH" value="/old/trace"/>
    <property name="TRACE_FILE_PREFIX" value="old"/>
    <property name="TRACE_FILE_SIZE" value="30MB"/>
</configuration>
""",
    )

    write_xml(
        after,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <property name="TRACE_PATH" value="/new/trace"/>
    <property name="TRACE_FILE_PREFIX" value="old"/>
    <property name="TRACE_FILE_SIZE" value="30MB"/>
</configuration>
""",
    )

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.NO_VERSION
    assert len(result.changes) == 1

    change = result.changes[0]

    assert change.change_type.value == "ATTRIBUTE_CHANGED"
    assert change.path == ("/configuration/property[@name='TRACE_PATH']")
    assert change.attribute == "value"
    assert change.before_value == "/old/trace"
    assert change.after_value == "/new/trace"


def test_element_attribute_change_is_detected(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    write_xml(
        before,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration scan="true">
</configuration>
""",
    )

    write_xml(
        after,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration scan="false">
</configuration>
""",
    )

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.NO_VERSION
    assert len(result.changes) == 1

    change = result.changes[0]

    assert change.change_type.value == "ATTRIBUTE_CHANGED"
    assert change.path == "/configuration"
    assert change.attribute == "scan"
    assert change.before_value == "true"
    assert change.after_value == "false"


def test_new_element_is_detected(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

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
        <port>8080</port>
        <host>localhost</host>
    </server>
</configuration>
""",
    )

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.NO_VERSION
    assert len(result.changes) == 1

    change = result.changes[0]

    assert change.change_type.value == "ADDED"
    assert change.path == "/configuration/server/host"
    assert change.before_value is None
    assert change.after_value == "localhost"


def test_removed_element_is_detected(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

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
        <port>8080</port>
    </server>
</configuration>
""",
    )

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.NO_VERSION
    assert len(result.changes) == 1

    change = result.changes[0]

    assert change.change_type.value == "REMOVED"
    assert change.path == "/configuration/server/host"
    assert change.before_value == "localhost"
    assert change.after_value is None


def test_formatting_only_change_is_ignored(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

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
<configuration><server>
<port>
    8080
</port>
<host>localhost</host>
</server></configuration>
""",
    )

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.NO_VERSION
    assert result.changes == []


def test_malformed_xml_is_rejected(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

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
""",
    )

    with pytest.raises(Exception):
        compare_xml_files(before, after)


def test_namespaced_elements_are_compared(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    write_xml(
        before,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration xmlns="http://example.com/config">
    <server>
        <port>8080</port>
    </server>
</configuration>
""",
    )

    write_xml(
        after,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration xmlns="http://example.com/config">
    <server>
        <port>9090</port>
    </server>
</configuration>
""",
    )

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.NO_VERSION
    assert len(result.changes) == 1

    change = result.changes[0]

    assert change.change_type.value == "VALUE_CHANGED"
    assert change.before_value == "8080"
    assert change.after_value == "9090"


def test_identifiable_element_reordering_is_ignored(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    write_xml(
        before,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <property name="TRACE_PATH" value="/trace"/>
    <property name="TRACE_FILE_PREFIX" value="app"/>
    <property name="TRACE_FILE_SIZE" value="30MB"/>
</configuration>
""",
    )

    write_xml(
        after,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <property name="TRACE_FILE_SIZE" value="30MB"/>
    <property name="TRACE_PATH" value="/trace"/>
    <property name="TRACE_FILE_PREFIX" value="app"/>
</configuration>
""",
    )

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.NO_VERSION
    assert result.changes == []


def test_changed_element_identity_is_add_and_remove(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    write_xml(
        before,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <property name="TRACE_PATH" value="/trace"/>
</configuration>
""",
    )

    write_xml(
        after,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <property name="TRACE_FILE" value="/trace"/>
</configuration>
""",
    )

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.NO_VERSION
    assert len(result.changes) == 2

    change_types = {change.change_type.value for change in result.changes}

    assert change_types == {"ADDED", "REMOVED"}


def test_same_element_name_under_different_parents_is_distinguished(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    write_xml(
        before,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <server>
        <property name="PATH" value="/server"/>
    </server>
    <client>
        <property name="PATH" value="/client"/>
    </client>
</configuration>
""",
    )

    write_xml(
        after,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <server>
        <property name="PATH" value="/server-new"/>
    </server>
    <client>
        <property name="PATH" value="/client"/>
    </client>
</configuration>
""",
    )

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.NO_VERSION
    assert len(result.changes) == 1

    change = result.changes[0]

    assert change.change_type.value == "ATTRIBUTE_CHANGED"
    assert change.path == ("/configuration/server/property[@name='PATH']")
    assert change.attribute == "value"
    assert change.before_value == "/server"
    assert change.after_value == "/server-new"


def test_multiple_xml_changes_are_detected(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    write_xml(
        before,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <server>
        <port>8080</port>
        <host>localhost</host>
    </server>
    <property name="TRACE_PATH" value="/old"/>
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
    <property name="TRACE_PATH" value="/new"/>
</configuration>
""",
    )

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.NO_VERSION
    assert len(result.changes) == 4

    change_types = {change.change_type.value for change in result.changes}

    assert change_types == {
        "VALUE_CHANGED",
        "ADDED",
        "ATTRIBUTE_CHANGED",
        "REMOVED",
    }


def test_multiple_xml_changes_are_detected(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    write_xml(
        before,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <server>
        <port>8080</port>
        <host>localhost</host>
    </server>
    <property name="TRACE_PATH" value="/old"/>
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
    <property name="TRACE_PATH" value="/new"/>
</configuration>
""",
    )

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.NO_VERSION
    assert len(result.changes) == 4

    change_types = {change.change_type.value for change in result.changes}

    assert change_types == {
        "VALUE_CHANGED",
        "ADDED",
        "ATTRIBUTE_CHANGED",
        "REMOVED",
    }


def test_attribute_added_is_detected(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    write_xml(
        before,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <server port="8080"/>
</configuration>
""",
    )

    write_xml(
        after,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <server port="8080" protocol="https"/>
</configuration>
""",
    )

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.NO_VERSION
    assert len(result.changes) == 1

    change = result.changes[0]

    assert change.change_type.value == "ATTRIBUTE_CHANGED"
    assert change.path == "/configuration/server"
    assert change.attribute == "protocol"
    assert change.before_value is None
    assert change.after_value == "https"


def test_attribute_removed_is_detected(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    write_xml(
        before,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <server port="8080" protocol="https"/>
</configuration>
""",
    )

    write_xml(
        after,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <server port="8080"/>
</configuration>
""",
    )

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.NO_VERSION
    assert len(result.changes) == 1

    change = result.changes[0]

    assert change.change_type.value == "ATTRIBUTE_CHANGED"
    assert change.path == "/configuration/server"
    assert change.attribute == "protocol"
    assert change.before_value == "https"
    assert change.after_value is None


def test_empty_element_value_is_compared(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    write_xml(
        before,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <server>
        <description/>
    </server>
</configuration>
""",
    )

    write_xml(
        after,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <server>
        <description>Production server</description>
    </server>
</configuration>
""",
    )

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.NO_VERSION
    assert len(result.changes) == 1

    change = result.changes[0]

    assert change.change_type.value == "VALUE_CHANGED"
    assert change.path == "/configuration/server/description"
    assert change.before_value == ""
    assert change.after_value == "Production server"


def test_comments_are_ignored(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    write_xml(
        before,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <!-- original comment -->
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
    <!-- completely different comment -->
    <server>
        <port>8080</port>
    </server>
</configuration>
""",
    )

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.NO_VERSION
    assert result.changes == []


def test_same_schema_reference_with_different_formatting_is_match(
    tmp_path,
):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

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
<configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="
        http://example.com/config
        example-config-1.0.xsd">
</configuration>
""",
    )

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.VERSION_MATCH
    assert result.changes == []


def test_no_namespace_schema_location_is_detected(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    write_xml(
        before,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:noNamespaceSchemaLocation="example-config-2.0.xsd">
    <server/>
</configuration>
""",
    )

    write_xml(
        after,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:noNamespaceSchemaLocation="example-config-2.0.xsd">
    <server/>
</configuration>
""",
    )

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.VERSION_MATCH
    assert result.changes == []


def test_different_root_elements_are_detected_structurally(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    write_xml(
        before,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <server/>
</configuration>
""",
    )

    write_xml(
        after,
        """<?xml version="1.0" encoding="UTF-8"?>
<settings>
    <server/>
</settings>
""",
    )

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.NO_VERSION

    change_types = {change.change_type.value for change in result.changes}

    assert change_types == {"ADDED", "REMOVED"}


def test_unchanged_xml_has_no_changes(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    content = """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <server port="8080">
        <host>localhost</host>
    </server>
    <property name="TRACE_PATH" value="/trace"/>
</configuration>
"""

    write_xml(before, content)
    write_xml(after, content)

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.NO_VERSION
    assert result.changes == []


def test_unknown_schema_is_excluded(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    write_xml(
        before,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://example.com/config example-config.xsd">
    <server>
        <port>8080</port>
    </server>
</configuration>
""",
    )

    write_xml(
        after,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://example.com/config example-config.xsd">
    <server>
        <port>9090</port>
    </server>
</configuration>
""",
    )

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.UNKNOWN_SCHEMA
    assert result.changes == []


def test_unknown_schema_on_one_side_is_excluded(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    write_xml(
        before,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <server/>
</configuration>
""",
    )

    write_xml(
        after,
        """<?xml version="1.0" encoding="UTF-8"?>
<configuration
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://example.com/config example-config.xsd">
    <server/>
</configuration>
""",
    )

    result = compare_xml_files(before, after)

    assert result.schema_status == XmlSchemaStatus.UNKNOWN_SCHEMA
    assert result.changes == []
