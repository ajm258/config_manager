from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import config_rationalizer.xml.rationalizer
from config_rationalizer.core.logging_config import AuditLogger
from config_rationalizer.properties.rationalizer import (
    FileRationalizationResult,
    _rationalize_file,
)
from config_rationalizer.xml.rationalizer import (
    _rationalize_file as _rationalize_xml_file,
)


@dataclass(frozen=True)
class FormatHandler:
    name: str
    extensions: tuple[str, ...]
    rationalize: Callable[..., FileRationalizationResult]


class HandlerRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, FormatHandler] = {}

    def register(self, handler: FormatHandler) -> None:
        for extension in handler.extensions:
            self._handlers[extension.lower()] = handler

    def get(self, extension: str) -> FormatHandler | None:
        return self._handlers.get(extension.lower())

    def supported_extensions(self) -> set[str]:
        return set(self._handlers)


def build_default_registry() -> HandlerRegistry:
    registry = HandlerRegistry()

    registry.register(
        FormatHandler(
            name="properties",
            extensions=(".properties",),
            rationalize=_rationalize_file,
        )
    )

    registry.register(
        FormatHandler(
            name="xml",
            extensions=(".xml",),
            rationalize=_rationalize_xml_file,
        )
    )

    return registry
