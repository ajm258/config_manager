from pathlib import Path
from urllib.parse import urlparse

from lxml import etree

from config_rationalizer.xml.models import XmlSchemaInfo
import re

XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"

XSI_SCHEMA_LOCATION = f"{{{XSI_NAMESPACE}}}schemaLocation"

XSI_NO_NAMESPACE_SCHEMA_LOCATION = f"{{{XSI_NAMESPACE}}}noNamespaceSchemaLocation"


def parse_xml(path: Path) -> etree._ElementTree:
    parser = etree.XMLParser(
        remove_blank_text=True,
        resolve_entities=False,
        no_network=True,
    )

    return etree.parse(
        str(path),
        parser,
    )


def _extract_schema_reference(
    root: etree._Element,
) -> str | None:
    schema_location = root.get(XSI_SCHEMA_LOCATION)

    if schema_location:
        parts = schema_location.split()

        # schemaLocation is namespace/location pairs.
        # The location is therefore every second value.
        if len(parts) >= 2:
            return parts[-1]

    no_namespace_location = root.get(XSI_NO_NAMESPACE_SCHEMA_LOCATION)

    if no_namespace_location:
        return no_namespace_location.strip()

    return None


def _extract_version(
    schema_reference: str | None,
) -> str | None:
    if not schema_reference:
        return None

    filename = Path(urlparse(schema_reference).path).name

    if not filename.endswith(".xsd"):
        return None

    stem = filename[:-4]

    parts = stem.rsplit("-", 1)

    if len(parts) != 2:
        return None

    version = parts[1].strip()

    if not re.fullmatch(r"\d+(?:\.\d+)*", version):
        return None

    return version


def parse_schema_info(
    tree: etree._ElementTree,
) -> XmlSchemaInfo:
    root = tree.getroot()

    schema_reference = _extract_schema_reference(root)

    version = _extract_version(schema_reference)

    namespace = root.nsmap.get(None)

    return XmlSchemaInfo(
        version=version,
        schema_reference=schema_reference,
        namespace=namespace,
        root_element=etree.QName(root).localname,
    )


def parse_xml_with_schema(
    path: Path,
) -> tuple[etree._ElementTree, XmlSchemaInfo]:
    tree = parse_xml(path)

    return tree, parse_schema_info(tree)


def has_schema_reference(
    schema_info: XmlSchemaInfo,
) -> bool:
    return schema_info.schema_reference is not None
