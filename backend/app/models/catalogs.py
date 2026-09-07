from app.core.time import utc_now

"""Модели справочников"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Numeric
from app.core.database import Base


class ExerciseCatalog(Base):
    """Справочник упражнений (площадка и город)"""

    __tablename__ = "exercise_catalog"

    id = Column(Integer, primary_key=True, index=True)
    context = Column(
        String(50), nullable=False, index=True, comment="training_ground или city"
    )
    short_name = Column(String(100), nullable=False)
    official_name = Column(
        String(500), nullable=False, comment="Полное официальное название"
    )
    paper_section = Column(String(255), nullable=True, comment="Раздел бумажной книжки")
    sort_order = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, default=True, nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    def __repr__(self):
        return f"<ExerciseCatalog {self.id}: {self.short_name} [{self.context}]>"


class SkillCatalog(Base):
    """Справочник критериев оценки навыков"""

    __tablename__ = "skill_catalog"

    id = Column(Integer, primary_key=True, index=True)
    context = Column(
        String(50), nullable=False, index=True, comment="training_ground или city"
    )
    name = Column(String(255), nullable=False)
    weight = Column(
        Numeric(5, 2), nullable=False, comment="Вес критерия в процентах (0-100)"
    )
    is_core = Column(
        Boolean, default=False, nullable=False, comment="Является ли ключевым критерием"
    )
    sort_order = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, default=True, nullable=False, index=True)
    version = Column(
        Integer, nullable=False, default=1, comment="Версия критерия для миграции"
    )

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    def __repr__(self):
        return (
            f"<SkillCatalog {self.id}: {self.name} ({self.weight}%) [{self.context}]>"
        )


class InterventionReasonCatalog(Base):
    """Справочник причин вмешательства инструктора"""

    __tablename__ = "intervention_reason_catalog"

    id = Column(Integer, primary_key=True, index=True)
    context = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    criticality = Column(
        String(50), nullable=False, comment="low, medium, high, critical"
    )
    active = Column(Boolean, default=True, nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    def __repr__(self):
        return (
            f"<InterventionReasonCatalog {self.id}: {self.name} [{self.criticality}]>"
        )


class VerdictCatalog(Base):
    """Справочник быстрых вердиктов после занятия"""

    __tablename__ = "verdict_catalog"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, default=True, nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    def __repr__(self):
        return f"<VerdictCatalog {self.id}: {self.name}>"


class ScoreFormulaVersion(Base):
    """Версия формулы расчёта Score"""

    __tablename__ = "score_formula_versions"

    version = Column(Integer, primary_key=True)
    valid_from = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Веса критериев (сериализованные JSON)
    ground_weights_json = Column(
        JSON, nullable=False, comment="Веса критериев площадки"
    )
    city_weights_json = Column(JSON, nullable=False, comment="Веса критериев города")
    overall_weights_json = Column(JSON, nullable=False, comment="Веса для общего Score")

    # Ограничения (caps)
    caps_json = Column(
        JSON,
        nullable=False,
        comment="Правила ограничений (самостоятельность, вмешательства)",
    )

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    def __repr__(self):
        return f"<ScoreFormulaVersion {self.version} valid from {self.valid_from}>"
