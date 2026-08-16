import argparse
from pathlib import Path

from .application import Application
from .core.enums import Format
from .core.exceptions import ConfigurationRationalizerError
from .core.logging_config import configure_logging
from .lifecycle.run import run_stage4
from .properties.comparator import compare_properties
from .properties.rationalizer import (
    rationalize_properties_directory,
)
from .reporting.json_report import (
    write_json_report,
    write_rationalization_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="config-rationalizer",
        description=("Safe post-upgrade configuration comparison and rationalization."),
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/rationalizer.yml"),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    init_parser = subparsers.add_parser(
        "init",
        help="Initialize a rationalization run.",
    )

    init_parser.add_argument("--profile", required=True)
    init_parser.add_argument("--upgrade-id", required=True)
    init_parser.add_argument(
        "--component",
        required=True,
        dest="target_component",
    )
    init_parser.add_argument(
        "--formats",
        default="properties,xml,yaml",
    )

    compare_parser = subparsers.add_parser(
        "compare-properties",
        help="Compare two properties files.",
    )

    compare_parser.add_argument(
        "--before",
        type=Path,
        required=True,
    )

    compare_parser.add_argument(
        "--after",
        type=Path,
        required=True,
    )

    compare_parser.add_argument(
        "--run-id",
        default="standalone",
    )

    compare_parser.add_argument(
        "--output",
        type=Path,
        required=True,
    )

    rationalize_parser = subparsers.add_parser(
        "rationalize-properties",
        help="Rationalize properties directories.",
    )

    rationalize_parser.add_argument(
        "--before",
        type=Path,
        required=True,
    )

    rationalize_parser.add_argument(
        "--after",
        type=Path,
        required=True,
    )

    rationalize_parser.add_argument(
        "--candidate",
        type=Path,
        required=True,
    )

    rationalize_parser.add_argument(
        "--run-id",
        default="standalone",
    )

    rationalize_parser.add_argument(
        "--output",
        type=Path,
        required=True,
    )

    run_parser = subparsers.add_parser(
        "run",
        help="Execute the complete post-deployment rationalization run.",
    )

    run_parser.add_argument(
        "--run-id",
        required=True,
    )

    run_parser.add_argument(
        "--upgrade-id",
        required=True,
    )

    run_parser.add_argument(
        "--profile",
        required=True,
    )

    run_parser.add_argument(
        "--component",
        required=True,
        dest="target_component",
    )

    run_parser.add_argument(
        "--stage0-backup",
        type=Path,
        required=True,
    )

    run_parser.add_argument(
        "--after",
        type=Path,
        required=True,
    )

    run_parser.add_argument(
        "--run-root",
        type=Path,
        required=True,
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

        if args.command == "compare-properties":
            result = compare_properties(
                args.before,
                args.after,
                run_id=args.run_id,
                audit=audit,
            )

            write_json_report(
                result,
                args.output,
            )

            print(f"Comparison status: {result.status}")
            print(f"Report: {args.output}")

            return 1 if result.status == "ERROR" else 0

        if args.command == "rationalize-properties":
            result = rationalize_properties_directory(
                args.before,
                args.after,
                args.candidate,
                run_id=args.run_id,
                audit=audit,
            )

            write_rationalization_report(
                result,
                args.output,
            )

            print(f"Rationalization status: {result.status}")
            print(f"Candidate directory: {args.candidate}")
            print(f"Report: {args.output}")

            return 1 if result.status == "COMPLETED_WITH_ERRORS" else 0

        if args.command == "run":
            from ruamel.yaml import YAML

            yaml = YAML(typ="safe")

            with args.config.open(
                "r",
                encoding="utf-8",
            ) as handle:
                config = yaml.load(handle) or {}

            configured_files = (
                config.get("files", {}).get("compare", {}).get("names", [])
            )

            result = run_stage4(
                run_id=args.run_id,
                upgrade_id=args.upgrade_id,
                profile=args.profile,
                target_component=args.target_component,
                stage0_backup=args.stage0_backup,
                after_root=args.after,
                run_root=args.run_root,
                configured_files=configured_files,
                audit=audit,
            )

            print(f"Run status: {result.status}")

            if result.errors:
                for error in result.errors:
                    print(f"ERROR: {error}")

            return 1 if result.status == "FAILED" else 0

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
