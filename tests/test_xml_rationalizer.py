from pathlib import Path

from lxml import etree

from config_rationalizer.xml.comparator import compare_xml_files
from config_rationalizer.xml.rationalizer import _apply_xml_changes


def write_xml(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def build_candidate(before: Path, after: Path):
    comparison = compare_xml_files(before, after)

    before_tree = etree.parse(
        str(before),
        etree.XMLParser(
            remove_blank_text=False,
            resolve_entities=False,
            no_network=True,
        ),
    )

    after_tree = etree.parse(
        str(after),
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

    return before_tree


def test_added_node_is_added_to_candidate(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    write_xml(
        before,
        """<configuration>
    <server>
        <port>8080</port>
    </server>
</configuration>
""",
    )

    write_xml(
        after,
        """<configuration>
    <server>
        <port>8080</port>
        <protocol>https</protocol>
    </server>
</configuration>
""",
    )

    candidate = build_candidate(before, after)

    assert candidate.xpath("/configuration/server/protocol")[0].text == "https"


def test_changed_value_is_reverted_to_master(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    write_xml(
        before,
        """<configuration>
    <server>
        <port>8080</port>
    </server>
</configuration>
""",
    )

    write_xml(
        after,
        """<configuration>
    <server>
        <port>9090</port>
    </server>
</configuration>
""",
    )

    candidate = build_candidate(before, after)

    assert candidate.xpath("/configuration/server/port")[0].text == "8080"


def test_removed_node_stays_removed(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    write_xml(
        before,
        """<configuration>
    <server>
        <port>8080</port>
        <host>localhost</host>
    </server>
</configuration>
""",
    )

    write_xml(
        after,
        """<configuration>
    <server>
        <port>8080</port>
    </server>
</configuration>
""",
    )

    candidate = build_candidate(before, after)

    assert candidate.xpath("/configuration/server/host") == []


def test_added_attribute_is_added_to_candidate(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    write_xml(
        before,
        """<configuration>
    <server port="8080"/>
</configuration>
""",
    )

    write_xml(
        after,
        """<configuration>
    <server port="8080" enabled="true"/>
</configuration>
""",
    )

    candidate = build_candidate(before, after)

    server = candidate.xpath("/configuration/server")[0]

    assert server.get("enabled") == "true"


def test_changed_attribute_is_reverted_to_master(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    write_xml(
        before,
        """<configuration>
    <server port="8080"/>
</configuration>
""",
    )

    write_xml(
        after,
        """<configuration>
    <server port="9090"/>
</configuration>
""",
    )

    candidate = build_candidate(before, after)

    server = candidate.xpath("/configuration/server")[0]

    assert server.get("port") == "8080"


def test_removed_attribute_stays_removed(tmp_path):
    before = tmp_path / "before.xml"
    after = tmp_path / "after.xml"

    write_xml(
        before,
        """<configuration>
    <server port="8080" enabled="true"/>
</configuration>
""",
    )

    write_xml(
        after,
        """<configuration>
    <server port="8080"/>
</configuration>
""",
    )

    candidate = build_candidate(before, after)

    server = candidate.xpath("/configuration/server")[0]

    assert server.get("enabled") is None
