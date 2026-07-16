"""Synthetic clinical patient record generator.

This module produces realistic-looking, entirely fictional patient
notes for use in the data ingestion pipeline. No real patient data is
used or referenced.
"""

import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from ingest.utils import ensure_directory, write_text_file

FIRST_NAMES: tuple[str, ...] = (
    "James",
    "Mary",
    "Robert",
    "Patricia",
    "John",
    "Jennifer",
    "Michael",
    "Linda",
    "David",
    "Elizabeth",
    "William",
    "Barbara",
    "Richard",
    "Susan",
    "Joseph",
    "Jessica",
    "Thomas",
    "Sarah",
    "Charles",
    "Karen",
)

LAST_NAMES: tuple[str, ...] = (
    "Smith",
    "Johnson",
    "Williams",
    "Brown",
    "Jones",
    "Garcia",
    "Miller",
    "Davis",
    "Rodriguez",
    "Martinez",
    "Hernandez",
    "Lopez",
    "Wilson",
    "Anderson",
    "Thomas",
    "Taylor",
    "Moore",
    "Jackson",
    "Martin",
    "Lee",
)

SEXES: tuple[str, ...] = ("Male", "Female")

CHIEF_COMPLAINTS: tuple[str, ...] = (
    "Chest pain",
    "Shortness of breath",
    "Persistent cough",
    "Abdominal pain",
    "Lower back pain",
    "Headache and dizziness",
    "Fatigue and generalized weakness",
    "Joint pain and swelling",
    "Fever and chills",
    "Nausea and vomiting",
)

MEDICAL_HISTORY_POOL: tuple[str, ...] = (
    "Hypertension",
    "Type 2 Diabetes Mellitus",
    "Hyperlipidemia",
    "Asthma",
    "Osteoarthritis",
    "Hypothyroidism",
    "Coronary Artery Disease",
    "Chronic Kidney Disease, Stage 2",
    "Gastroesophageal Reflux Disease",
    "Generalized Anxiety Disorder",
    "Major Depressive Disorder",
    "Obesity",
    "Seasonal Allergic Rhinitis",
)

MEDICATIONS_POOL: tuple[str, ...] = (
    "Lisinopril 10mg daily",
    "Metformin 500mg twice daily",
    "Atorvastatin 20mg nightly",
    "Albuterol inhaler as needed",
    "Levothyroxine 75mcg daily",
    "Omeprazole 20mg daily",
    "Amlodipine 5mg daily",
    "Sertraline 50mg daily",
    "Metoprolol 25mg twice daily",
    "Ibuprofen 400mg as needed",
)

ALLERGIES_POOL: tuple[str, ...] = (
    "Penicillin",
    "Sulfa drugs",
    "Latex",
    "Peanuts",
    "Shellfish",
    "Aspirin",
    "Codeine",
    "No known drug allergies",
)

PLAN_OPTIONS: tuple[str, ...] = (
    "Continue current medication regimen and monitor symptoms.",
    "Order laboratory panel including CBC and comprehensive metabolic panel.",
    "Schedule follow-up visit in two weeks.",
    "Refer to specialist for further evaluation.",
    "Adjust medication dosage and reassess in four weeks.",
    "Advise lifestyle modification including diet and exercise.",
    "Order imaging studies to further evaluate presenting symptoms.",
)


@dataclass(frozen=True)
class PatientRecord:
    """A single synthetic patient clinical record.

    Attributes:
        patient_id: Unique identifier for the patient, e.g. "patient_001".
        name: Patient's full name.
        age: Patient's age in years.
        sex: Patient's sex.
        visit_dates: Chronologically ordered visit dates.
        chief_complaint: Primary reason for the visit.
        medical_history: List of relevant past medical conditions.
        medications: List of current medications.
        allergies: List of known allergies.
        vitals: Mapping of vital sign names to their recorded values.
        assessment: Clinical assessment narrative.
        plan: Clinical plan narrative.
    """

    patient_id: str
    name: str
    age: int
    sex: str
    visit_dates: list[str]
    chief_complaint: str
    medical_history: list[str]
    medications: list[str]
    allergies: list[str]
    vitals: dict[str, str]
    assessment: str
    plan: str


def _generate_visit_dates(rng: random.Random) -> list[str]:
    """Generate a chronologically ordered list of visit dates.

    Args:
        rng: Random number generator instance used for reproducibility.

    Returns:
        list[str]: Visit dates formatted as "YYYY-MM-DD".
    """
    visit_count = rng.randint(1, 3)
    today = date.today()
    offsets = sorted(rng.sample(range(1, 730), k=visit_count), reverse=True)
    return [(today - timedelta(days=offset)).isoformat() for offset in offsets]


def _generate_vitals(rng: random.Random) -> dict[str, str]:
    """Generate a set of plausible vital sign readings.

    Args:
        rng: Random number generator instance used for reproducibility.

    Returns:
        dict[str, str]: Mapping of vital sign names to formatted values.
    """
    systolic = rng.randint(100, 150)
    diastolic = rng.randint(60, 95)
    heart_rate = rng.randint(58, 100)
    temperature = round(rng.uniform(97.0, 99.5), 1)
    respiratory_rate = rng.randint(12, 20)
    oxygen_saturation = rng.randint(94, 100)

    return {
        "blood_pressure": f"{systolic}/{diastolic} mmHg",
        "heart_rate": f"{heart_rate} bpm",
        "temperature": f"{temperature} F",
        "respiratory_rate": f"{respiratory_rate} breaths/min",
        "oxygen_saturation": f"{oxygen_saturation}%",
    }


def _generate_single_patient_record(patient_number: int, rng: random.Random) -> PatientRecord:
    """Generate a single synthetic patient record.

    Args:
        patient_number: 1-indexed sequence number for the patient.
        rng: Random number generator instance used for reproducibility.

    Returns:
        PatientRecord: The generated synthetic patient record.
    """
    patient_id = f"patient_{patient_number:03d}"
    name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
    age = rng.randint(18, 90)
    sex = rng.choice(SEXES)
    chief_complaint = rng.choice(CHIEF_COMPLAINTS)
    medical_history = rng.sample(MEDICAL_HISTORY_POOL, k=rng.randint(1, 4))
    medications = rng.sample(MEDICATIONS_POOL, k=rng.randint(1, 4))
    allergies = rng.sample(ALLERGIES_POOL, k=rng.randint(1, 2))
    vitals = _generate_vitals(rng)

    assessment = (
        f"Patient presents with {chief_complaint.lower()}, clinically "
        f"correlated with a history of {medical_history[0].lower()}. "
        "The overall clinical picture is consistent with a stable, "
        "chronic condition requiring ongoing management."
    )
    plan = " ".join(rng.sample(PLAN_OPTIONS, k=rng.randint(2, 3)))

    return PatientRecord(
        patient_id=patient_id,
        name=name,
        age=age,
        sex=sex,
        visit_dates=_generate_visit_dates(rng),
        chief_complaint=chief_complaint,
        medical_history=medical_history,
        medications=medications,
        allergies=allergies,
        vitals=vitals,
        assessment=assessment,
        plan=plan,
    )


def generate_patient_records(count: int, seed: int | None = None) -> list[PatientRecord]:
    """Generate a list of synthetic patient records.

    Args:
        count: Number of patient records to generate.
        seed: Optional random seed for reproducible generation.

    Returns:
        list[PatientRecord]: The generated synthetic patient records.
    """
    rng = random.Random(seed)
    return [_generate_single_patient_record(number, rng) for number in range(1, count + 1)]


def _format_bullet_list(items: list[str]) -> str:
    """Format a list of strings as a newline-separated bullet list.

    Args:
        items: Items to format.

    Returns:
        str: Bullet-formatted text block.
    """
    return "\n".join(f"- {item}" for item in items)


def _format_vitals(vitals: dict[str, str]) -> str:
    """Format a vitals mapping as a newline-separated bullet list.

    Args:
        vitals: Mapping of vital sign names to formatted values.

    Returns:
        str: Bullet-formatted text block.
    """
    labels = {
        "blood_pressure": "Blood Pressure",
        "heart_rate": "Heart Rate",
        "temperature": "Temperature",
        "respiratory_rate": "Respiratory Rate",
        "oxygen_saturation": "Oxygen Saturation",
    }
    return "\n".join(f"- {labels[key]}: {value}" for key, value in vitals.items())


def format_patient_record(record: PatientRecord) -> str:
    """Render a patient record as a formatted clinical note.

    Args:
        record: The patient record to format.

    Returns:
        str: The formatted clinical note text.
    """
    return (
        f"Patient ID: {record.patient_id}\n"
        f"Name: {record.name}\n"
        f"Age: {record.age}\n"
        f"Sex: {record.sex}\n"
        f"Visit Dates: {', '.join(record.visit_dates)}\n"
        "\n"
        "Chief Complaint:\n"
        f"{record.chief_complaint}\n"
        "\n"
        "Medical History:\n"
        f"{_format_bullet_list(record.medical_history)}\n"
        "\n"
        "Medications:\n"
        f"{_format_bullet_list(record.medications)}\n"
        "\n"
        "Allergies:\n"
        f"{_format_bullet_list(record.allergies)}\n"
        "\n"
        "Vital Signs:\n"
        f"{_format_vitals(record.vitals)}\n"
        "\n"
        "Assessment:\n"
        f"{record.assessment}\n"
        "\n"
        "Plan:\n"
        f"{record.plan}\n"
    )


def save_patient_records(records: list[PatientRecord], output_dir: Path) -> list[Path]:
    """Write patient records to disk as individual text files.

    Args:
        records: Patient records to persist.
        output_dir: Directory in which to write the patient files.

    Returns:
        list[Path]: Paths to the written patient files, in the same
            order as the input records.
    """
    ensure_directory(output_dir)
    saved_paths: list[Path] = []

    for record in records:
        file_path = output_dir / f"{record.patient_id}.txt"
        write_text_file(file_path, format_patient_record(record))
        saved_paths.append(file_path)

    return saved_paths
