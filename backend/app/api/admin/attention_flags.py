from app.core.time import utc_now

"""Endpoints для управления флагами внимания"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.audit import audit_log
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.models import AttentionFlag, Client, SkillCatalog
from app.api.admin.dependencies import get_current_admin
from app.services.attention_flag_manager import AttentionFlagManager

router = APIRouter()


class AttentionFlagResponse(BaseModel):
    """Ответ с флагом внимания"""

    id: int
    client_id: int
    client_name: str
    context: str
    skill_name: str | None
    reason: str
    active: bool
    opened_at: str
    closed_at: str | None
    closed_reason: str | None

    class Config:
        from_attributes = True


@router.get("/attention-flags", response_model=List[AttentionFlagResponse])
async def list_attention_flags(
    active_only: bool = True,
    context: str | None = None,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список всех флагов внимания

    Params:
    - active_only: показывать только активные флаги (по умолчанию True)
    - context: фильтр по контексту ("Учебная площадка" / "Город")
    """
    query = select(AttentionFlag)

    if active_only:
        query = query.where(AttentionFlag.active == True)

    if context:
        query = query.where(AttentionFlag.context == context)

    query = query.order_by(AttentionFlag.opened_at.desc())

    result = await db.execute(query)
    flags = result.scalars().all()

    # Загружаем связанные данные
    response = []
    for flag in flags:
        client = await db.get(Client, flag.client_id)
        skill_name = None

        if flag.skill_id:
            skill = await db.get(SkillCatalog, flag.skill_id)
            if skill:
                skill_name = skill.name

        response.append(
            AttentionFlagResponse(
                id=flag.id,
                client_id=flag.client_id,
                client_name=client.full_name if client else "Неизвестно",
                context=flag.context,
                skill_name=skill_name,
                reason=flag.reason,
                active=flag.active,
                opened_at=flag.opened_at.isoformat(),
                closed_at=flag.closed_at.isoformat() if flag.closed_at else None,
                closed_reason=flag.closed_reason,
            )
        )

    return response


@router.get(
    "/clients/{client_id}/attention-flags", response_model=List[AttentionFlagResponse]
)
async def get_client_attention_flags(
    client_id: int,
    active_only: bool = True,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Получить флаги внимания для конкретного клиента"""
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    flag_manager = AttentionFlagManager(db)

    if active_only:
        flags = await flag_manager.get_active_flags(client_id)
    else:
        query = (
            select(AttentionFlag)
            .where(AttentionFlag.client_id == client_id)
            .order_by(AttentionFlag.opened_at.desc())
        )
        result = await db.execute(query)
        flags = result.scalars().all()

    response = []
    for flag in flags:
        skill_name = None
        if flag.skill_id:
            skill = await db.get(SkillCatalog, flag.skill_id)
            if skill:
                skill_name = skill.name

        response.append(
            AttentionFlagResponse(
                id=flag.id,
                client_id=flag.client_id,
                client_name=client.full_name,
                context=flag.context,
                skill_name=skill_name,
                reason=flag.reason,
                active=flag.active,
                opened_at=flag.opened_at.isoformat(),
                closed_at=flag.closed_at.isoformat() if flag.closed_at else None,
                closed_reason=flag.closed_reason,
            )
        )

    return response


@router.post("/attention-flags/{flag_id}/close")
async def close_attention_flag(
    flag_id: int,
    reason: str = Query(..., min_length=3, max_length=1000),
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Вручную закрыть флаг внимания

    Body:
    - reason: причина закрытия
    """
    flag = await db.get(AttentionFlag, flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    if not flag.active:
        raise HTTPException(status_code=400, detail="Flag is already closed")

    flag.active = False
    flag.closed_at = utc_now()
    flag.closed_reason = reason
    await audit_log(
        db,
        "admin",
        0,
        "attention_flag",
        flag.id,
        "close",
        old_values={"active": True},
        new_values={"active": False},
        reason=reason,
    )

    await db.commit()

    return {"status": "ok", "message": "Flag closed successfully"}
