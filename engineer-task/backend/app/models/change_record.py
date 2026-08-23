from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ChangeRecord(Base):
    """Append-only, project-scoped record of an incremental evidence change."""
    __tablename__ = "change_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fact_type: Mapped[str] = mapped_column(String(80))
    old_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_document: Mapped[str | None] = mapped_column(String(255), nullable=True)
    review_status: Mapped[str] = mapped_column(String(50), default="recorded")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
