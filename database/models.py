"""SQLAlchemy ORM models for Clinical Copilot's persisted data.

This module is responsible ONLY for defining the User, Conversation,
and Query tables and their relationships. It contains no engine,
session, CRUD, or FastAPI dependency-injection logic.
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import CHAR, TypeDecorator

from database.base import Base


class GUID(TypeDecorator):
    """A platform-independent GUID column type.

    Uses PostgreSQL's native UUID type in production, and falls back to
    a 36-character string representation for other dialects (such as
    SQLite, used in tests), so the same ORM models can be exercised
    without a live PostgreSQL instance.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """Choose the concrete column type for the active dialect."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        """Convert a UUID (or UUID-like string) into its stored form."""
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value)
        if not isinstance(value, uuid.UUID):
            return str(uuid.UUID(str(value)))
        return str(value)

    def process_result_value(self, value, dialect):
        """Convert a stored value back into a `uuid.UUID` instance."""
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


class User(Base):
    """A registered Clinical Copilot user account.

    Attributes:
        id: Unique user identifier.
        email: The user's unique email address.
        full_name: The user's display name, when known.
        hashed_password: Bcrypt password hash, or None for
            OAuth-only accounts.
        provider: Authentication provider, e.g. "local" or "google".
        created_at: Timestamp the account was created.
        updated_at: Timestamp the account was last updated.
        conversations: Conversations owned by this user.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="local")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Conversation(Base):
    """A conversation session belonging to a user.

    Attributes:
        id: Unique conversation identifier.
        user_id: Identifier of the owning user.
        title: Optional human-readable conversation title.
        created_at: Timestamp the conversation was created.
        updated_at: Timestamp the conversation was last updated.
        user: The owning user.
        queries: Queries recorded within this conversation.
    """

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="conversations")
    queries: Mapped[list["Query"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class Query(Base):
    """A single question/answer turn recorded within a conversation.

    Attributes:
        id: Unique query identifier.
        conversation_id: Identifier of the owning conversation.
        query_text: The user's question (transcribed, for voice turns).
        response_text: The agent's generated answer.
        citations: Formatted citation strings supporting the answer.
        evaluation: Evaluation metrics computed for the answer.
        latency_ms: Wall-clock time, in milliseconds, taken to answer.
        created_at: Timestamp the query was recorded.
        conversation: The owning conversation.
    """

    __tablename__ = "queries"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evaluation: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="queries")
