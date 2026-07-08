"""Audio file loading and validation.

This module is responsible ONLY for validating that an audio file
exists, is in a supported format, and is minimally readable. It
contains no transcription, memory, session, or pipeline orchestration
logic.
"""

from pathlib import Path

_MAGIC_BYTE_CHECKS: dict[str, tuple[bytes, ...]] = {
    "wav": (b"RIFF",),
    "mp3": (b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"),
    "m4a": (b"ftyp",),
}


class AudioValidationError(Exception):
    """Raised when an audio file fails validation."""


def validate_audio_file(
    path: Path, supported_formats: tuple[str, ...]
) -> bytes:
    """Validate an audio file's existence, format, and basic readability.

    Args:
        path: Path to the audio file.
        supported_formats: File extensions accepted, without leading
            dots (e.g. ("wav", "mp3", "m4a")).

    Returns:
        bytes: The raw audio file contents, once validated.

    Raises:
        AudioValidationError: If the file does not exist, has an
            unsupported extension, is empty, or its contents do not
            match the expected format signature for its extension.
    """
    if not path.exists() or not path.is_file():
        raise AudioValidationError(f"Audio file not found: {path}")

    extension = path.suffix.lower().lstrip(".")
    if extension not in supported_formats:
        raise AudioValidationError(
            f"Unsupported audio format '.{extension}'. "
            f"Supported formats: {', '.join(supported_formats)}."
        )

    try:
        content = path.read_bytes()
    except OSError as error:
        raise AudioValidationError(f"Could not read audio file: {path}") from error

    if not content:
        raise AudioValidationError(f"Audio file is empty: {path}")

    signatures = _MAGIC_BYTE_CHECKS.get(extension)
    if signatures is not None:
        header = content[:12]
        if not any(signature in header for signature in signatures):
            raise AudioValidationError(
                f"File '{path}' does not appear to be a valid '.{extension}' "
                "audio file (unexpected file signature)."
            )

    return content