"""Configurable catalogs with version snapshots and immutable historical labels."""

from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models import (
    ExerciseCatalog,
    SkillCatalog,
    VerdictCatalog,
    InterventionReasonCatalog,
    ScoreFormulaVersion,
)
from app.api.admin.dependencies import get_current_admin
from app.services.audit import audit_log
from app.services.score_engine import DEFAULT_CAPS, RECENCY_WEIGHTS

router = APIRouter()
MODELS = {
    "exercises": ExerciseCatalog,
    "skills": SkillCatalog,
    "verdicts": VerdictCatalog,
    "reasons": InterventionReasonCatalog,
}


class CatalogInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    context: Literal["Учебная площадка", "Город"] = "Учебная площадка"
    name: str | None = Field(default=None, max_length=255)
    short_name: str | None = Field(default=None, max_length=100)
    official_name: str | None = Field(default=None, max_length=500)
    paper_section: str | None = Field(default=None, max_length=255)
    weight: float = Field(default=10, gt=0, le=100)
    is_core: bool = False
    sort_order: int = Field(default=0, ge=0, le=1000)
    active: bool = True
    criticality: Literal["low", "medium", "high", "critical"] = "medium"
    reason: str = Field(default="Настройка справочника", min_length=3, max_length=1000)


def model_for(kind):
    if kind not in MODELS:
        raise HTTPException(404, "Справочник не найден")
    return MODELS[kind]


def payload(item):
    keys = [
        "id",
        "context",
        "name",
        "short_name",
        "official_name",
        "paper_section",
        "weight",
        "is_core",
        "active",
        "sort_order",
        "version",
        "criticality",
    ]
    return {
        key: float(getattr(item, key)) if key == "weight" else getattr(item, key)
        for key in keys
        if hasattr(item, key)
    }


async def formula_version(db):
    # Lock the criteria rows so concurrent catalog edits cannot reuse a version.
    await db.execute(
        select(SkillCatalog.id).order_by(SkillCatalog.id).with_for_update()
    )
    skills = list(
        (
            await db.execute(select(SkillCatalog).where(SkillCatalog.active.is_(True)))
        ).scalars()
    )
    number = (
        await db.execute(select(func.max(ScoreFormulaVersion.version)))
    ).scalar() or 0
    version = ScoreFormulaVersion(
        version=number + 1,
        ground_weights_json={
            str(s.id): payload(s) for s in skills if s.context == "Учебная площадка"
        },
        city_weights_json={
            str(s.id): payload(s) for s in skills if s.context == "Город"
        },
        overall_weights_json={"training_ground": 0.4, "city": 0.6},
        caps_json={**DEFAULT_CAPS, "recency_weights": RECENCY_WEIGHTS},
    )
    db.add(version)
    await db.flush()
    return version.version


@router.get("/catalogs/{kind}")
async def list_catalog(
    kind: str,
    context: str | None = None,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    model = model_for(kind)
    query = select(model)
    if context and hasattr(model, "context"):
        query = query.where(model.context == context)
    return [
        payload(item) for item in (await db.execute(query.order_by(model.id))).scalars()
    ]


async def save_item(db, kind, request, item=None):
    model = model_for(kind)
    if kind == "skills":
        await db.execute(
            select(SkillCatalog.id).order_by(SkillCatalog.id).with_for_update()
        )
        if item:
            await db.refresh(item)
    if kind == "exercises" and not (request.short_name and request.official_name):
        raise HTTPException(422, "Заполните короткое и полное название упражнения")
    if kind != "exercises" and not request.name:
        raise HTTPException(422, "Укажите название")
    fields = request.model_dump(exclude={"reason"})
    fields = {key: value for key, value in fields.items() if hasattr(model, key)}
    old = payload(item) if item else None
    if item:
        if hasattr(item, "context") and item.context != request.context:
            raise HTTPException(
                422, "Для другого контекста создайте новый элемент справочника"
            )
        for key, value in fields.items():
            setattr(item, key, value)
        if kind == "skills":
            item.version += 1
    else:
        item = model(**fields)
        db.add(item)
    await db.flush()
    if kind == "skills":
        await formula_version(db)
    await audit_log(
        db,
        "admin",
        0,
        kind,
        item.id,
        "update" if old else "create",
        old_values=old,
        new_values=payload(item),
        reason=request.reason,
    )
    await db.commit()
    return payload(item)


@router.post("/catalogs/{kind}")
async def create_item(
    kind: str,
    request: CatalogInput,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    return await save_item(db, kind, request)


@router.patch("/catalogs/{kind}/{item_id}")
async def update_item(
    kind: str,
    item_id: int,
    request: CatalogInput,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(model_for(kind), item_id)
    if not item:
        raise HTTPException(404, "Элемент не найден")
    return await save_item(db, kind, request, item)
