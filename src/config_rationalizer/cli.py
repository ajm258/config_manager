import argparse
from pathlib import Path

from .application import Application
from .core.enums import Format
from .core.exceptions import ConfigurationRationalizerError
from .core.logging_config import configure_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="config-rationalizer",
        description=(
            "Safe post-upgrade configuration comparison "
            "and rationalization."
        ),
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/rationalizer.yml"),
        help="Path to rationalizer configuration.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    init_parser = subparsers.add_parser(
        "init",
        help="Initialize a rationalization run.",
    )

    init_parser.add_argument(
        "--profile",
        required=True,
    )

    init_parser.add_argument(
        "--upgrade-id",
        required=True,
    )

    init_parser.add_argument(
        "--component",
        required=True,
        dest="target_component",
    )

    init_parser.add_argument(
        "--formats",
        default="properties,xml,yaml",
        help="Comma-separated formats.",
    )

    return parser


def parse_formats(value: str) -> list[Format]:
    formats: list[Format] = []

    for item in value.split(","):
        name = item.strip().lower()

        try:
            formats.append(Format(name))
        except ValueError as exc:
            raise ValueError(f"Unknown format: {name}") from exc

    return formats


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    audit = configure_logging()

    try:
        if args.command == "init":
            formats = parse_formats(args.formats)

            application = Application(
                config_path=args.config,
                audit=audit,
            )

            metadata = application.initialize_run(
                profile=args.profile,
                upgrade_id=args.upgrade_id,
                target_component=args.target_component,
                formats=formats,
            )

            print(f"Run initialized: {metadata.run_id}")
            return 0

        parser.error(f"Unsupported command: {args.command}")

    except ConfigurationRationalizerError as exc:
        audit.event(
            "COMMAND_FAILED",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        print(f"ERROR: {exc}")
        return 1

    except ValueError as exc:
        audit.event(
            "COMMAND_VALIDATION_FAILED",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())