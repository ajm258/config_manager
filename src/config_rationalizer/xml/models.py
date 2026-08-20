from dataclasses import dataclass
from enum import Enum


class XmlSchemaStatus(str, Enum):
    VERSION_MATCH = "VERSION_MATCH"
    VERSION_CHANGED = "VERSION_CHANGED"
    NO_VERSION = "NO_VERSION"
    VERSION_MISSING_ON_ONE_SIDE = "VERSION_MISSING_ON_ONE_SIDE"
    PARSE_ERROR = "PARSE_ERROR"


class XmlChangeType(str, Enum):
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    VALUE_CHANGED = "VALUE_CHANGED"
    ATTRIBUTE_CHANGED = "ATTRIBUTE_CHANGED"


@dataclass(frozen=True)
class XmlSchemaInfo:
    version: str | None
    schema_reference: str | None
    namespace: str | None
    root_element: str


@dataclass(frozen=True)
class XmlElementChange:
    change_type: XmlChangeType
    path: str
    before_value: str | None
    after_value: str | None
    attribute: str | None = None


@dataclass(frozen=True)
class XmlComparisonResult:
    schema_status: XmlSchemaStatus
    before_schema: XmlSchemaInfo | None
    after_schema: XmlSchemaInfo | None
    changes: list[XmlElementChange]
