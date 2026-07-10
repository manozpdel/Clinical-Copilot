"""Tests for synthetic patient record generation."""

from pathlib import Path

from ingest.generator import generate_patient_records, save_patient_records


def test_generate_patient_records_returns_requested_count() -> None:
    """Generating records should return exactly the requested count."""
    records = generate_patient_records(5)

    assert len(records) == 5


def test_generated_record_has_required_fields() -> None:
    """Each generated record should contain all required clinical fields."""
    record = generate_patient_records(1)[0]

    assert record.patient_id == "patient_001"
    assert record.name
    assert 0 < record.age < 120
    assert record.sex in {"Male", "Female"}
    assert record.visit_dates
    assert record.chief_complaint
    assert record.medical_history
    assert record.medications
    assert record.allergies
    assert record.vitals
    assert record.assessment
    assert record.plan


def test_save_patient_records_writes_expected_files(tmp_path: Path) -> None:
    """Saved patient records should produce correctly named, populated files."""
    records = generate_patient_records(3)
    output_dir = tmp_path / "patients"

    saved_paths = save_patient_records(records, output_dir)

    assert len(saved_paths) == 3
    for path, record in zip(saved_paths, records, strict=True):
        assert path.exists()
        assert path.name == f"{record.patient_id}.txt"
        content = path.read_text(encoding="utf-8")
        assert record.patient_id in content
        assert record.name in content
