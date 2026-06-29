"""Task DB model — persists A2A Task proto state."""

from datetime import datetime, timezone

from sqlalchemy import Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from a2a_mesh.db.base import Base


class TaskRecord(Base):
    """Stores a serialized A2A Task proto as JSON.

    One row per task. The full proto is stored in `data` so we don't need
    to mirror every proto field into columns — we only index what we query on.
    """

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    context_id: Mapped[str] = mapped_column(String(64), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="submitted")
    data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-serialized Task proto
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_tasks_context_id", "context_id"),
        Index("ix_tasks_agent_id", "agent_id"),
        Index("ix_tasks_state", "state"),
    )
