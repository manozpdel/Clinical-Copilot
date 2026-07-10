"""Tests for audio file loading and validation."""

from pathlib import Path

import pytest

from voice.audio import AudioValidationError, validate_audio_file

_SUPPORTED = ("wav", "mp3", "m4a")


def test_validate_audio_file_raises_when_missing(tmp_path: Path) -> None:
    """A nonexistent audio file should raise a validation error."""
    missing_path = tmp_path / "missing.wav"

    with pytest.raises(AudioValidationError):
        validate_audio_file(missing_path, _SUPPORTED)


def test_validate_audio_file_raises_for_unsupported_extension(
    tmp_path: Path,
) -> None:
    """An unsupported file extension should raise a validation error."""
    file_path = tmp_path / "clip.ogg"
    file_path.write_bytes(b"some content")

    with pytest.raises(AudioValidationError):
        validate_audio_file(file_path, _SUPPORTED)


def test_validate_audio_file_raises_for_empty_file(tmp_path: Path) -> None:
    """An empty audio file should raise a validation error."""
    file_path = tmp_path / "clip.wav"
    file_path.write_bytes(b"")

    with pytest.raises(AudioValidationError):
        validate_audio_file(file_path, _SUPPORTED)


def test_validate_audio_file_raises_for_bad_signature(tmp_path: Path) -> None:
    """A .wav file without a valid RIFF header should raise a validation error."""
    file_path = tmp_path / "clip.wav"
    file_path.write_bytes(b"not a real wav file")

    with pytest.raises(AudioValidationError):
        validate_audio_file(file_path, _SUPPORTED)


def test_validate_audio_file_accepts_valid_wav(tmp_path: Path) -> None:
    """A file with a valid RIFF header should pass validation."""
    file_path = tmp_path / "clip.wav"
    file_path.write_bytes(b"RIFF" + b"\x00" * 40)

    content = validate_audio_file(file_path, _SUPPORTED)

    assert content.startswith(b"RIFF")


def test_validate_audio_file_accepts_valid_m4a(tmp_path: Path) -> None:
    """A file with a valid ftyp header should pass validation."""
    file_path = tmp_path / "clip.m4a"
    file_path.write_bytes(b"\x00\x00\x00\x18ftypM4A " + b"\x00" * 20)

    content = validate_audio_file(file_path, _SUPPORTED)

    assert b"ftyp" in content[:12]
