"""Company model."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from a2a_mesh.db.base import Base


class Company(Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    namespace: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plan: Mapped[str] = mapped_column(String(32), nullable=False, default="free")

    users: Mapped[list["User"]] = relationship("User", back_populates="company")  # type: ignore[name-defined]
    agents: Mapped[list["Agent"]] = relationship("Agent", back_populates="company")  # type: ignore[name-defined]
