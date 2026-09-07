from app.core.time import utc_now

"""Модели аудита и временного доступа"""
from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class AuditLog(Base):
    """Журнал аудита критических изменений"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Кто изменил
    actor_type = Column(
        String(50), nullable=False, comment="admin, instructor или system"
    )
    actor_id = Column(Integer, nullable=False)

    # Что изменил
    entity_type = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Тип сущности (booking, report и т.д.)",
    )
    entity_id = Column(Integer, nullable=False, index=True)
    action = Column(String(50), nullable=False, comment="create, update, delete")

    # Изменения
    old_json = Column(JSON, nullable=True, comment="Старые значения")
    new_json = Column(JSON, nullable=True, comment="Новые значения")
    reason = Column(Text, nullable=True, comment="Причина изменения")

    created_at = Column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )

    def __repr__(self):
        return f"<AuditLog {self.id}: {self.actor_type}/{self.actor_id} {self.action} {self.entity_type}/{self.entity_id}>"


class AccessGrant(Base):
    """Временный повторный доступ инструктора к карточке клиента"""

    __tablename__ = "access_grants"

    id = Column(Integer, primary_key=True, index=True)
    instructor_id = Column(
        Integer, ForeignKey("instructors.id"), nullable=False, index=True
    )
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    booking_id = Column(
        Integer,
        ForeignKey("bookings.id"),
        nullable=True,
        comment="Конкретная запись или null для общего доступа",
    )

    # Временные рамки
    valid_from = Column(DateTime(timezone=True), nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=False, index=True)

    # Метаданные
    reason = Column(Text, nullable=False, comment="Причина выдачи повторного доступа")
    granted_by_admin_id = Column(Integer, nullable=False, comment="Кто выдал доступ")
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    instructor = relationship("Instructor", back_populates="access_grants")
    client = relationship("Client", back_populates="access_grants")
    booking = relationship("Booking", back_populates="access_grants")

    def __repr__(self):
        return f"<AccessGrant {self.id}: Instructor {self.instructor_id} -> Client {self.client_id} until {self.valid_until}>"
