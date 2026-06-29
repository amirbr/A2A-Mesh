"""Agent model."""

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from a2a_mesh.db.base import Base


class Agent(Base):
    __tablename__ = "agents"

    company_id: Mapped[str] = mapped_column(String(32), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="stopped")
    visibility: Mapped[str] = mapped_column(String(32), nullable=False, default="private")
    runtime: Mapped[str] = mapped_column(String(32), nullable=False, default="managed")
    config: Mapped[str] = mapped_column(Text, nullable=False, default="{}")  # JSON
    endpoint_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    company: Mapped["Company"] = relationship("Company", back_populates="agents")  # type: ignore[name-defined]

    __table_args__ = (
        Index("ix_agents_company_id", "company_id"),
        Index("ix_agents_status", "status"),
    )
