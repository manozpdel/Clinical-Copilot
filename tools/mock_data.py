"""Realistic synthetic clinical data shared across all mock tools.

This module is responsible ONLY for generating and holding the shared
mock patient population. It contains no tool implementation,
registration, routing, validation, or retry logic. Every mock tool
(EHR, Notes, Wearables) reads from the same `MOCK_PATIENTS` mapping so
that a given patient ID resolves consistently across all three.
"""

import random
from datetime import date, timedelta
from typing import Any

_PATIENT_COUNT = 20
_SEED = 42

_FIRST_NAMES: tuple[str, ...] = (
    "Alice",
    "Brian",
    "Carla",
    "Derek",
    "Elena",
    "Farid",
    "Grace",
    "Hassan",
    "Isla",
    "Jamal",
    "Kira",
    "Liam",
    "Maya",
    "Noah",
    "Omar",
    "Priya",
    "Quinn",
    "Rosa",
    "Sam",
    "Tara",
)

_LAST_NAMES: tuple[str, ...] = (
    "Nguyen",
    "Patel",
    "Kowalski",
    "Silva",
    "Okafor",
    "Muller",
    "Rossi",
    "Kim",
    "Haddad",
    "Andersson",
    "Costa",
    "Novak",
    "Chen",
    "Ibrahim",
    "Larsen",
    "Fischer",
    "Suzuki",
    "Diallo",
    "Moreno",
    "Wallace",
)

_MEDICAL_HISTORY_POOL: tuple[str, ...] = (
    "Hypertension",
    "Type 2 Diabetes Mellitus",
    "Hyperlipidemia",
    "Asthma",
    "Osteoarthritis",
    "Hypothyroidism",
    "Coronary Artery Disease",
    "Chronic Kidney Disease, Stage 2",
    "GERD",
    "Generalized Anxiety Disorder",
)

_MEDICATIONS_POOL: tuple[str, ...] = (
    "Lisinopril 10mg daily",
    "Metformin 500mg twice daily",
    "Atorvastatin 20mg nightly",
    "Albuterol inhaler as needed",
    "Levothyroxine 75mcg daily",
    "Omeprazole 20mg daily",
    "Amlodipine 5mg daily",
    "Sertraline 50mg daily",
)

_ALLERGIES_POOL: tuple[str, ...] = (
    "Penicillin",
    "Sulfa drugs",
    "Latex",
    "Peanuts",
    "Shellfish",
    "No known drug allergies",
)

_CHIEF_COMPLAINTS: tuple[str, ...] = (
    "Chest pain",
    "Shortness of breath",
    "Persistent cough",
    "Abdominal pain",
    "Lower back pain",
    "Headache and dizziness",
    "Fatigue and generalized weakness",
    "Joint pain and swelling",
)


def _generate_patient_id(index: int) -> str:
    """Build a zero-padded mock patient ID.

    Args:
        index: 1-indexed sequence number for the patient.

    Returns:
        str: A patient ID in the format "P0001".
    """
    return f"P{index:04d}"


def _generate_ehr_record(rng: random.Random) -> dict[str, Any]:
    """Generate a mock EHR record for a single patient.

    Args:
        rng: Random number generator instance used for reproducibility.

    Returns:
        dict[str, Any]: Demographics, medical history, medications,
            allergies, and a lab summary.
    """
    return {
        "demographics": {
            "name": f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)}",
            "age": rng.randint(18, 90),
            "sex": rng.choice(("Male", "Female")),
        },
        "medical_history": rng.sample(_MEDICAL_HISTORY_POOL, k=rng.randint(1, 4)),
        "medications": rng.sample(_MEDICATIONS_POOL, k=rng.randint(1, 3)),
        "allergies": rng.sample(_ALLERGIES_POOL, k=rng.randint(1, 2)),
        "lab_summary": {
            "glucose_mg_dl": rng.randint(80, 180),
            "total_cholesterol_mg_dl": rng.randint(140, 260),
            "creatinine_mg_dl": round(rng.uniform(0.6, 1.4), 2),
        },
    }


def _generate_notes(rng: random.Random) -> list[dict[str, Any]]:
    """Generate mock clinical visit notes for a single patient.

    Args:
        rng: Random number generator instance used for reproducibility.

    Returns:
        list[dict[str, Any]]: One or two visit note records, each with
            a date, chief complaint, assessment, and plan.
    """
    today = date.today()
    visit_count = rng.randint(1, 2)
    notes: list[dict[str, Any]] = []

    for offset_index in range(visit_count):
        visit_date = today - timedelta(days=rng.randint(10, 400) * (offset_index + 1))
        complaint = rng.choice(_CHIEF_COMPLAINTS)
        notes.append(
            {
                "date": visit_date.isoformat(),
                "chief_complaint": complaint,
                "assessment": (
                    f"Clinical picture consistent with {complaint.lower()}, "
                    "stable on current management."
                ),
                "plan": "Continue current regimen; follow up in 4 weeks.",
            }
        )

    return notes


def _generate_wearables(rng: random.Random) -> dict[str, Any]:
    """Generate mock wearable device data for a single patient.

    Args:
        rng: Random number generator instance used for reproducibility.

    Returns:
        dict[str, Any]: Resting heart rate, blood pressure, sleep,
            activity, and a 7-day daily trend series.
    """
    today = date.today()
    daily_trends = [
        {
            "date": (today - timedelta(days=day_offset)).isoformat(),
            "steps": rng.randint(2000, 12000),
            "resting_heart_rate": rng.randint(55, 90),
        }
        for day_offset in range(6, -1, -1)
    ]

    return {
        "heart_rate_bpm": rng.randint(55, 95),
        "blood_pressure": f"{rng.randint(105, 145)}/{rng.randint(65, 90)} mmHg",
        "sleep_hours": round(rng.uniform(4.5, 8.5), 1),
        "daily_steps": rng.randint(2000, 12000),
        "daily_trends": daily_trends,
    }


def _generate_mock_patients() -> dict[str, dict[str, Any]]:
    """Generate the full mock patient population.

    Returns:
        dict[str, dict[str, Any]]: A mapping of patient ID to a record
            containing "ehr", "notes", and "wearables" sections.
    """
    rng = random.Random(_SEED)
    patients: dict[str, dict[str, Any]] = {}

    for index in range(1, _PATIENT_COUNT + 1):
        patient_id = _generate_patient_id(index)
        patients[patient_id] = {
            "ehr": _generate_ehr_record(rng),
            "notes": _generate_notes(rng),
            "wearables": _generate_wearables(rng),
        }

    return patients


MOCK_PATIENTS: dict[str, dict[str, Any]] = _generate_mock_patients()
