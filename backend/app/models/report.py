import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), unique=True)
    themes: Mapped[list] = mapped_column(JSON, default=list)
    competitor_activities: Mapped[list] = mapped_column(JSON, default=list)
    raw_sources: Mapped[dict] = mapped_column(JSON, default=dict)
    hallucination_verdict: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
