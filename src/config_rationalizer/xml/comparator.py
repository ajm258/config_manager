from collections import Counter
from pathlib import Path

from lxml import etree

from config_rationalizer.xml.models import (
    XmlChangeType,
    XmlComparisonResult,
    XmlElementChange,
    XmlSchemaInfo,
    XmlSchemaStatus,
)
from config_rationalizer.xml.parser import (
    XSI_NO_NAMESPACE_SCHEMA_LOCATION,
    XSI_SCHEMA_LOCATION,
    parse_xml_with_schema,
)


def _element_name(
    element: etree._Element,
) -> str:
    return etree.QName(element).localname


def _element_segment(
    element: etree._Element,
    occurrence: int,
) -> str:
    """
    Build a stable structural identity.

    Relevant identifying attributes are included when present.
    Otherwise sibling occurrence is used.
    """
    name = _element_name(element)

    for attribute in (
        "name",
        "id",
        "key",
        "jndi-name",
    ):
        value = element.get(attribute)

        if value is not None:
            return f"{name}[@{attribute}='{value}']"

    if any(
        element.get(attribute) is not None
        for attribute in ("name", "id", "key", "jndi-name")
    ):
        for attribute in (
            "name",
            "id",
            "key",
            "jndi-name",
        ):
            value = element.get(attribute)

            if value is not None:
                return f"{name}[@{attribute}='{value}']"

    if occurrence == 1:
        return name

    return f"{name}[{occurrence}]"


def _build_element_map(
    root: etree._Element,
) -> dict[str, etree._Element]:
    result: dict[str, etree._Element] = {}

    def visit(
        element: etree._Element,
        parent_path: str,
    ) -> None:
        siblings = (
            [child for child in element.getparent() if isinstance(child.tag, str)]
            if element.getparent() is not None
            else []
        )

        same_name = [
            sibling
            for sibling in siblings
            if _element_name(sibling) == _element_name(element)
        ]

        occurrence = same_name.index(element) + 1 if element in same_name else 1

        segment = _element_segment(
            element,
            occurrence,
        )

        path = f"{parent_path}/{segment}"

        result[path] = element

        child_counts: Counter[str] = Counter()

        for child in element:
            if not isinstance(child.tag, str):
                continue

            child_name = _element_name(child)

            child_counts[child_name] += 1

            visit(
                child,
                path,
            )

    visit(root, "")

    return result


def _element_value(
    element: etree._Element,
) -> str:
    return element.text.strip() if element.text and element.text.strip() else ""


def _compare_attributes(
    before: etree._Element,
    after: etree._Element,
    path: str,
) -> list[XmlElementChange]:
    changes: list[XmlElementChange] = []

    names = set(before.attrib) | set(after.attrib)

    for name in sorted(names):
        before_value = before.get(name)
        after_value = after.get(name)

        if name in {
            XSI_SCHEMA_LOCATION,
            XSI_NO_NAMESPACE_SCHEMA_LOCATION,
        }:
            continue

        if before_value == after_value:
            continue

        changes.append(
            XmlElementChange(
                change_type=(XmlChangeType.ATTRIBUTE_CHANGED),
                path=path,
                before_value=before_value,
                after_value=after_value,
                attribute=name,
            )
        )

    return changes


def compare_xml_files(
    before_path: Path,
    after_path: Path,
) -> XmlComparisonResult:
    before_tree, before_schema = parse_xml_with_schema(before_path)

    after_tree, after_schema = parse_xml_with_schema(after_path)

    before_version = before_schema.version
    after_version = after_schema.version

    before_has_schema = before_schema.schema_reference is not None
    after_has_schema = after_schema.schema_reference is not None

    # No schema reference on either side.
    if not before_has_schema and not after_has_schema:
        schema_status = XmlSchemaStatus.NO_VERSION

    # A schema reference exists, but its identity/version
    # cannot be determined reliably.
    elif (before_has_schema and before_version is None) or (
        after_has_schema and after_version is None
    ):
        return XmlComparisonResult(
            schema_status=XmlSchemaStatus.UNKNOWN_SCHEMA,
            before_schema=before_schema,
            after_schema=after_schema,
            changes=[],
        )

    # A schema is present on only one side.
    elif before_has_schema != after_has_schema:
        return XmlComparisonResult(
            schema_status=XmlSchemaStatus.VERSION_MISSING_ON_ONE_SIDE,
            before_schema=before_schema,
            after_schema=after_schema,
            changes=[],
        )

    # Both sides have a known schema identity.
    elif before_version != after_version:
        return XmlComparisonResult(
            schema_status=XmlSchemaStatus.VERSION_CHANGED,
            before_schema=before_schema,
            after_schema=after_schema,
            changes=[],
        )

    else:
        schema_status = XmlSchemaStatus.VERSION_MATCH

    before_map = _build_element_map(before_tree.getroot())

    after_map = _build_element_map(after_tree.getroot())

    changes: list[XmlElementChange] = []

    paths = set(before_map) | set(after_map)

    for path in sorted(paths):
        before = before_map.get(path)
        after = after_map.get(path)

        if before is None:
            changes.append(
                XmlElementChange(
                    change_type=XmlChangeType.ADDED,
                    path=path,
                    before_value=None,
                    after_value=_element_value(after),
                )
            )
            continue

        if after is None:
            changes.append(
                XmlElementChange(
                    change_type=XmlChangeType.REMOVED,
                    path=path,
                    before_value=_element_value(before),
                    after_value=None,
                )
            )
            continue

        changes.extend(
            _compare_attributes(
                before,
                after,
                path,
            )
        )

        before_value = _element_value(before)
        after_value = _element_value(after)

        if before_value != after_value:
            changes.append(
                XmlElementChange(
                    change_type=XmlChangeType.VALUE_CHANGED,
                    path=path,
                    before_value=before_value,
                    after_value=after_value,
                )
            )

    return XmlComparisonResult(
        schema_status=schema_status,
        before_schema=before_schema,
        after_schema=after_schema,
        changes=changes,
    )
