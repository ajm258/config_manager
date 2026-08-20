from collections.abc import Mapping, Sequence
from typing import Any


REDACTED = "[REDACTED]"


class Redactor:
    """Central redaction service for audit logs and reports."""

    def __init__(self, patterns: Sequence[str] = ()) -> None:
        self._patterns = tuple(pattern.casefold() for pattern in patterns if pattern)

    def is_sensitive(self, name: str | None) -> bool:
        if not name:
            return False

        value = name.casefold()

        return any(pattern in value for pattern in self._patterns)

    def redact(
        self,
        name: str | None,
        value: Any,
    ) -> Any:
        if self.is_sensitive(name):
            return REDACTED

        return value

    def redact_mapping(
        self,
        values: Mapping[str, Any],
    ) -> dict[str, Any]:
        return {key: self.redact(key, value) for key, value in values.items()}
