"""Filesystem helper utilities used throughout the ingestion pipeline."""

from pathlib import Path


def ensure_directory(path: Path) -> Path:
    """Ensure a directory exists, creating parent directories as needed.

    Args:
        path: Directory path to create if it does not already exist.

    Returns:
        Path: The same directory path, guaranteed to exist.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_text_file(path: Path, content: str) -> None:
    """Write UTF-8 text content to a file.

    Args:
        path: Destination file path.
        content: Text content to write.
    """
    path.write_text(content, encoding="utf-8")


def read_text_file(path: Path) -> str:
    """Read UTF-8 text content from a file.

    Args:
        path: Source file path.

    Returns:
        str: The file's text content.
    """
    return path.read_text(encoding="utf-8")


def list_text_files(directory: Path) -> list[Path]:
    """List all `.txt` files in a directory, sorted by name.

    Args:
        directory: Directory to search.

    Returns:
        list[Path]: Sorted list of `.txt` file paths found in the
            directory.
    """
    return sorted(directory.glob("*.txt"))
