from app.core.time import utc_now

"""Модели итоговых заключений и ИИ-черновиков"""
from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship

from app.core.database import Base


class FinalConclusion(Base):
    """Итоговое заключение школы о готовности ученика"""

    __tablename__ = "final_conclusions"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)

    # Заключение
    status = Column(
        String(255), nullable=False, comment="Рекомендованный статус готовности"
    )
    text = Column(Text, nullable=False, comment="Полный текст заключения")

    # Кто утвердил
    ai_draft_id = Column(
        Integer,
        ForeignKey("ai_drafts.id"),
        nullable=True,
        comment="Если основано на ИИ-черновике",
    )
    approved_by_type = Column(
        String(50), nullable=False, comment="admin или instructor"
    )
    approved_by_id = Column(
        Integer, nullable=False, comment="ID администратора или инструктора"
    )

    # Версионность
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    client = relationship("Client", back_populates="conclusions")
    ai_draft = relationship("AIDraft", foreign_keys=[ai_draft_id])

    def __repr__(self):
        return (
            f"<FinalConclusion {self.id} v{self.version} for Client {self.client_id}>"
        )


class AIDraft(Base):
    """ИИ-черновик итогового заключения"""

    __tablename__ = "ai_drafts"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)

    # Параметры генерации
    provider = Column(String(50), nullable=False, comment="groq или nvidia")
    model = Column(String(100), nullable=False, comment="Название модели")
    prompt_version = Column(String(50), nullable=False, comment="Версия промпта")
    input_hash = Column(
        String(64), nullable=False, comment="Хеш входных данных для кеша"
    )

    # Результат
    generated_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    client = relationship("Client", back_populates="ai_drafts")

    def __repr__(self):
        return f"<AIDraft {self.id} for Client {self.client_id} via {self.provider}>"
