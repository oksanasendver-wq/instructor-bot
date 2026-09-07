from app.core.time import utc_now

"""Модель записи на занятие"""
from sqlalchemy import (
    Column,
    Integer,
    Date,
    Time,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Numeric,
    Text,
)
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


def enum_values(enum_class):
    """Сохраняет в PostgreSQL значения enum, а не имена Python-констант."""
    return [member.value for member in enum_class]


class BookingStatus(str, enum.Enum):
    """Статус записи"""

    PLANNED = "planned"
    ARRIVAL_WINDOW = "arrival_window"
    IN_PROGRESS = "in_progress"
    NO_SHOW = "no_show"
    ASSESSMENT_REQUIRED = "assessment_required"
    COMPLETED = "completed"
    ADMIN_REVIEW_REQUIRED = "admin_review_required"


class Context(str, enum.Enum):
    """Контекст занятия"""

    TRAINING_GROUND = "Учебная площадка"
    CITY = "Город"


class TransmissionType(str, enum.Enum):
    """Тип КПП"""

    MANUAL = "МКПП"
    AUTOMATIC = "АКПП"


class PaymentType(str, enum.Enum):
    """Источник оплаты"""

    CASH = "наличные"
    PACKAGE = "пакет"
    CERTIFICATE = "сертификат"
    ALREADY_PAID = "уже оплачено"
    OTHER = "другое"


class PaymentStatus(str, enum.Enum):
    """Статус оплаты"""

    PENDING = "pending"
    RECEIVED = "received"
    NOT_REQUIRED = "not_required"


class Booking(Base):
    """Запись на занятие"""

    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    instructor_id = Column(
        Integer, ForeignKey("instructors.id"), nullable=False, index=True
    )

    # Дата и время
    date = Column(Date, nullable=False, index=True)
    start_at = Column(Time, nullable=False)
    end_at = Column(Time, nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=60)

    # Контекст занятия
    context = Column(SQLEnum(Context, values_callable=enum_values), nullable=False)
    transmission = Column(
        SQLEnum(TransmissionType, values_callable=enum_values), nullable=False
    )
    vehicle_id = Column(
        Integer, nullable=True, comment="ID автомобиля (опционально в прототипе)"
    )

    # Оплата
    payment_type = Column(
        SQLEnum(PaymentType, values_callable=enum_values), nullable=False
    )
    amount_due = Column(Numeric(10, 2), nullable=False, default=0)
    payment_status = Column(
        SQLEnum(PaymentStatus, values_callable=enum_values),
        nullable=False,
        default=PaymentStatus.PENDING,
    )

    # Статус и метаданные
    status = Column(
        SQLEnum(BookingStatus, values_callable=enum_values),
        nullable=False,
        default=BookingStatus.PLANNED,
        index=True,
    )
    admin_comment = Column(
        Text, nullable=True, comment="Служебная заметка администратора"
    )
    arrived_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    client = relationship("Client", back_populates="bookings")
    instructor = relationship(
        "Instructor", back_populates="bookings", foreign_keys=[instructor_id]
    )
    report = relationship(
        "LessonReport",
        back_populates="booking",
        uselist=False,
        cascade="all, delete-orphan",
    )
    access_grants = relationship(
        "AccessGrant", back_populates="booking", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Booking {self.id}: {self.date} {self.start_at}-{self.end_at} [{self.status.value}]>"
