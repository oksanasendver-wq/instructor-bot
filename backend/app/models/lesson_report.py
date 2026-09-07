from app.core.time import utc_now

"""Модель отчёта о занятии"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Enum as SQLEnum,
    Text,
    SmallInteger,
    Boolean,
    DateTime,
)
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base
from .booking import Context


def enum_values(enum_class):
    """Сохраняет в PostgreSQL значения enum, а не имена Python-констант."""
    return [member.value for member in enum_class]


class AutonomyLevel(str, enum.Enum):
    """Уровень самостоятельности"""

    A0 = "A0 — постоянная помощь"
    A1 = "A1 — частые подсказки"
    A2 = "A2 — редкие подсказки"
    A3 = "A3 — самостоятельно"


class InterventionType(str, enum.Enum):
    """Тип вмешательства инструктора"""

    NONE = "нет"
    VERBAL = "словесная подсказка"
    PHYSICAL = "физическое вмешательство"


class LessonReport(Base):
    """Отчёт инструктора после занятия"""

    __tablename__ = "lesson_reports"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(
        Integer, ForeignKey("bookings.id"), unique=True, nullable=False, index=True
    )
    instructor_id = Column(
        Integer, ForeignKey("instructors.id"), nullable=False, index=True
    )
    context = Column(SQLEnum(Context, values_callable=enum_values), nullable=False)

    # Оценки
    overall_grade_1_5 = Column(
        SmallInteger, nullable=False, comment="Общая оценка занятия 1-5"
    )
    autonomy_level = Column(
        SQLEnum(AutonomyLevel, values_callable=enum_values), nullable=False
    )

    # Вердикт и комментарий
    quick_verdict = Column(
        String(255), nullable=True, comment="Краткий вердикт из справочника"
    )
    comment_internal = Column(
        Text, nullable=True, comment="Внутренний текстовый комментарий"
    )

    # Метаданные
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    edited_until = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="До какого времени можно редактировать",
    )
    last_edited_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    booking = relationship("Booking", back_populates="report")
    instructor = relationship("Instructor", back_populates="reports")
    exercises = relationship(
        "LessonExercise", back_populates="report", cascade="all, delete-orphan"
    )
    skill_assessments = relationship(
        "SkillAssessment", back_populates="report", cascade="all, delete-orphan"
    )
    interventions = relationship(
        "Intervention", back_populates="report", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<LessonReport {self.id} for Booking {self.booking_id}>"


class LessonExercise(Base):
    """Упражнение, отработанное на занятии"""

    __tablename__ = "lesson_exercises"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(
        Integer, ForeignKey("lesson_reports.id"), nullable=False, index=True
    )
    exercise_id = Column(Integer, ForeignKey("exercise_catalog.id"), nullable=False)
    official_name_snapshot = Column(
        String(500), nullable=False, comment="Snapshot названия на момент занятия"
    )

    # Relationships
    report = relationship("LessonReport", back_populates="exercises")
    exercise_catalog = relationship("ExerciseCatalog")

    def __repr__(self):
        return f"<LessonExercise {self.id}: {self.official_name_snapshot}>"


class SkillAssessment(Base):
    """Оценка навыка на занятии"""

    __tablename__ = "skill_assessments"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(
        Integer, ForeignKey("lesson_reports.id"), nullable=False, index=True
    )
    skill_id = Column(
        Integer, ForeignKey("skill_catalog.id"), nullable=False, index=True
    )
    value_0_4 = Column(SmallInteger, nullable=False, comment="Оценка 0-4")
    skill_version = Column(
        Integer, nullable=False, default=1, comment="Версия критерия"
    )

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    report = relationship("LessonReport", back_populates="skill_assessments")
    skill_catalog = relationship("SkillCatalog")

    def __repr__(self):
        return (
            f"<SkillAssessment {self.id}: skill={self.skill_id} value={self.value_0_4}>"
        )


class Intervention(Base):
    """Вмешательство инструктора на занятии"""

    __tablename__ = "interventions"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(
        Integer, ForeignKey("lesson_reports.id"), nullable=False, index=True
    )
    type = Column(
        SQLEnum(InterventionType, values_callable=enum_values), nullable=False
    )
    reason = Column(
        String(255), nullable=True, comment="Причина вмешательства из справочника"
    )
    is_critical = Column(
        Boolean, default=False, nullable=False, comment="Критическое событие"
    )
    description = Column(Text, nullable=True, comment="Дополнительное описание")

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    report = relationship("LessonReport", back_populates="interventions")

    def __repr__(self):
        return f"<Intervention {self.id}: {self.type.value} {'[CRITICAL]' if self.is_critical else ''}>"
