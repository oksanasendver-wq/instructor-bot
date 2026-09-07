from app.core.time import utc_now

"""Модель инструктора"""
from sqlalchemy import (
    BigInteger,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


def enum_values(enum_class):
    """Сохраняет в PostgreSQL значения enum, а не имена Python-констант."""
    return [member.value for member in enum_class]


class TransmissionType(str, enum.Enum):
    """Тип КПП"""

    MANUAL = "МКПП"
    AUTOMATIC = "АКПП"


class Instructor(Base):
    """Инструктор автошколы"""

    __tablename__ = "instructors"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    telegram_user_id = Column(BigInteger, unique=True, nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    transmission = Column(
        SQLEnum(TransmissionType, values_callable=enum_values), nullable=True
    )
    avatar_url = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    bookings = relationship(
        "Booking", back_populates="instructor", foreign_keys="[Booking.instructor_id]"
    )
    reports = relationship("LessonReport", back_populates="instructor")
    access_grants = relationship("AccessGrant", back_populates="instructor")

    def __repr__(self):
        return f"<Instructor {self.id}: {self.full_name}>"
