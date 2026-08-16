from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DiscoveredFile:
    path: Path
    relative_path: Path
    filename: str
    extension: str


def discover_files(root: Path) -> list[DiscoveredFile]:
    """
    Recursively discover files beneath root.

    File type is determined from the filename extension at runtime.
    """
    if not root.exists():
        raise FileNotFoundError(f"Configuration directory does not exist: {root}")

    if not root.is_dir():
        raise NotADirectoryError(f"Configuration path is not a directory: {root}")

    files: list[DiscoveredFile] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue

        relative_path = path.relative_to(root)

        files.append(
            DiscoveredFile(
                path=path,
                relative_path=relative_path,
                filename=path.name,
                extension=path.suffix.lower(),
            )
        )

    return files


def select_files(
    files: list[DiscoveredFile],
    configured_names: list[str],
) -> tuple[list[DiscoveredFile], list[DiscoveredFile]]:
    """
    Select files by filename.

    Empty configured_names means all discovered files are selected.

    Matching is filename + extension only; directory path is ignored.
    """
    names = {name.strip() for name in configured_names if name.strip()}

    if not names:
        return files, []

    selected = [item for item in files if item.filename in names]

    skipped = [item for item in files if item.filename not in names]

    return selected, skipped
