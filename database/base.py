"""Declarative base for all SQLAlchemy ORM models.

This module is responsible ONLY for defining the shared declarative
base class. It contains no engine, session, model, or CRUD logic.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base class for all ORM models."""
