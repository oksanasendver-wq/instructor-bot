"""Endpoints для каталогов (упражнения, критерии, вердикты)"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.models import (
    ExerciseCatalog,
    SkillCatalog,
    VerdictCatalog,
    InterventionReasonCatalog,
)
from app.api.instructor.dependencies import get_current_instructor

router = APIRouter()


class ExerciseResponse(BaseModel):
    """Ответ с упражнением"""

    id: int
    short_name: str
    official_name: str
    context: str

    class Config:
        from_attributes = True


class SkillResponse(BaseModel):
    """Ответ с критерием оценки"""

    id: int
    name: str
    weight: float
    is_core: bool
    context: str

    class Config:
        from_attributes = True


class VerdictResponse(BaseModel):
    """Ответ с вердиктом"""

    id: int
    name: str

    class Config:
        from_attributes = True


class InterventionReasonResponse(BaseModel):
    """Ответ с причиной вмешательства"""

    id: int
    name: str
    criticality: str
    context: str

    class Config:
        from_attributes = True


@router.get("/exercises", response_model=dict)
async def get_exercises(
    context: str = Query(..., description="Контекст: 'Учебная площадка' или 'Город'"),
    instructor: dict = Depends(get_current_instructor),
    db: AsyncSession = Depends(get_db),
):
    """Получить список упражнений для контекста"""
    query = (
        select(ExerciseCatalog)
        .where(ExerciseCatalog.context == context, ExerciseCatalog.active == True)
        .order_by(ExerciseCatalog.sort_order)
    )

    result = await db.execute(query)
    exercises = result.scalars().all()

    return {
        "exercises": [
            ExerciseResponse(
                id=e.id,
                short_name=e.short_name,
                official_name=e.official_name,
                context=e.context,
            )
            for e in exercises
        ]
    }


@router.get("/skills", response_model=dict)
async def get_skills(
    context: str = Query(..., description="Контекст: 'Учебная площадка' или 'Город'"),
    instructor: dict = Depends(get_current_instructor),
    db: AsyncSession = Depends(get_db),
):
    """Получить список критериев оценки для контекста"""
    query = (
        select(SkillCatalog)
        .where(SkillCatalog.context == context, SkillCatalog.active == True)
        .order_by(SkillCatalog.sort_order)
    )

    result = await db.execute(query)
    skills = result.scalars().all()

    return {
        "skills": [
            SkillResponse(
                id=s.id,
                name=s.name,
                weight=float(s.weight),
                is_core=s.is_core,
                context=s.context,
            )
            for s in skills
        ]
    }


@router.get("/verdicts", response_model=dict)
async def get_verdicts(
    instructor: dict = Depends(get_current_instructor),
    db: AsyncSession = Depends(get_db),
):
    """Получить список быстрых вердиктов"""
    query = (
        select(VerdictCatalog)
        .where(VerdictCatalog.active == True)
        .order_by(VerdictCatalog.sort_order)
    )

    result = await db.execute(query)
    verdicts = result.scalars().all()

    return {"verdicts": [VerdictResponse(id=v.id, name=v.name) for v in verdicts]}


@router.get("/intervention-reasons", response_model=dict)
async def get_intervention_reasons(
    context: str = Query(..., description="Контекст: 'Учебная площадка' или 'Город'"),
    instructor: dict = Depends(get_current_instructor),
    db: AsyncSession = Depends(get_db),
):
    """Получить список причин вмешательства для контекста"""
    query = select(InterventionReasonCatalog).where(
        InterventionReasonCatalog.context == context,
        InterventionReasonCatalog.active == True,
    )

    result = await db.execute(query)
    reasons = result.scalars().all()

    return {
        "reasons": [
            InterventionReasonResponse(
                id=r.id, name=r.name, criticality=r.criticality, context=r.context
            )
            for r in reasons
        ]
    }
