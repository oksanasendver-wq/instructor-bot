from app.core.time import utc_now

"""Модель клиента"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class Client(Base):
    """Клиент (ученик) автошколы"""

    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    notes_internal = Column(Text, nullable=True, comment="Внутренние заметки о клиенте")
    is_archived = Column(Boolean, nullable=False, default=False, server_default="false")

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    bookings = relationship(
        "Booking", back_populates="client", cascade="all, delete-orphan"
    )
    score_snapshots = relationship(
        "ScoreSnapshot", back_populates="client", cascade="all, delete-orphan"
    )
    attention_flags = relationship(
        "AttentionFlag", back_populates="client", cascade="all, delete-orphan"
    )
    conclusions = relationship(
        "FinalConclusion", back_populates="client", cascade="all, delete-orphan"
    )
    ai_drafts = relationship(
        "AIDraft", back_populates="client", cascade="all, delete-orphan"
    )
    access_grants = relationship(
        "AccessGrant", back_populates="client", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Client {self.id}: {self.full_name}>"
