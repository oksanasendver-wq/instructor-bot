from app.core.time import utc_now

"""Модели для системы оценок"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Boolean,
    DateTime,
    Numeric,
    Text,
    JSON,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class ScoreSnapshot(Base):
    """Snapshot рассчитанного Score"""

    __tablename__ = "score_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    context = Column(
        String(50),
        nullable=False,
        index=True,
        comment="training_ground, city или overall",
    )

    # Score данные
    score = Column(Numeric(5, 2), nullable=False, comment="Рассчитанный балл 0-100")
    status = Column(
        String(50), nullable=False, comment="Предварительный, Формируется, Достоверный"
    )
    formula_version = Column(Integer, nullable=False, comment="Версия формулы расчёта")

    # Snapshot исходных данных для воспроизводимости
    inputs_json = Column(JSON, nullable=False, comment="Исходные оценки и данные")
    caps_json = Column(JSON, nullable=True, comment="Применённые ограничения")

    calculated_at = Column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )

    # Relationships
    client = relationship("Client", back_populates="score_snapshots")

    def __repr__(self):
        return (
            f"<ScoreSnapshot {self.id}: {self.context} = {self.score} [{self.status}]>"
        )


class AttentionFlag(Base):
    """Флаг 'Требует внимания' для повторяющихся проблем"""

    __tablename__ = "attention_flags"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    context = Column(String(50), nullable=False, comment="training_ground или city")

    # Что требует внимания
    skill_id = Column(Integer, ForeignKey("skill_catalog.id"), nullable=True)
    reason = Column(String(500), nullable=False, comment="Описание проблемы")

    # Статус
    active = Column(Boolean, default=True, nullable=False, index=True)
    opened_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    closed_reason = Column(
        Text, nullable=True, comment="Почему закрыт (улучшение, ошибка)"
    )

    # Relationships
    client = relationship("Client", back_populates="attention_flags")
    skill_catalog = relationship("SkillCatalog")

    def __repr__(self):
        status = "ACTIVE" if self.active else "CLOSED"
        return f"<AttentionFlag {self.id}: {self.reason} [{status}]>"
