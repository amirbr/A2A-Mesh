"""User model."""

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from a2a_mesh.db.base import Base


class User(Base):
    __tablename__ = "users"

    company_id: Mapped[str] = mapped_column(String(32), ForeignKey("companies.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="member")

    company: Mapped["Company"] = relationship("Company", back_populates="users")  # type: ignore[name-defined]

    __table_args__ = (Index("ix_users_company_id", "company_id"),)
