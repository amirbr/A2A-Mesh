"""Pipeline and PipelineRun SQLAlchemy models."""

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from a2a_mesh.core.ids import pipeline_id, run_id
from a2a_mesh.db.base import Base


class Pipeline(Base):
    """A named sequence of agent steps."""

    __tablename__ = "pipelines"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=pipeline_id)
    company_id: Mapped[str] = mapped_column(String(32), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    steps: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    __table_args__ = (
        Index("ix_pipelines_company_id", "company_id"),
    )

    def get_steps(self) -> list[dict[str, Any]]:
        """Return steps as a list of dicts."""
        return json.loads(self.steps)  # type: ignore[no-any-return]

    def set_steps(self, steps: list[dict[str, Any]]) -> None:
        self.steps = json.dumps(steps)


class PipelineRun(Base):
    """A single execution of a pipeline."""

    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=run_id)
    pipeline_id: Mapped[str] = mapped_column(String(32), ForeignKey("pipelines.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    input: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_pipeline_runs_pipeline_id", "pipeline_id"),
        Index("ix_pipeline_runs_status", "status"),
    )
