"""Сервис для аудита изменений"""

from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def audit_log(
    db: AsyncSession,
    actor_type: str,  # admin, instructor, system
    actor_id: int,
    entity_type: str,
    entity_id: int,
    action: str,  # create, update, delete
    old_values: Optional[Dict] = None,
    new_values: Optional[Dict] = None,
    reason: Optional[str] = None,
):
    """
    Создаёт запись в журнале аудита

    Args:
        db: сессия БД
        actor_type: тип актора (admin/instructor/system)
        actor_id: ID актора
        entity_type: тип сущности (booking, report, client и т.д.)
        entity_id: ID сущности
        action: действие (create/update/delete)
        old_values: старые значения (для update/delete)
        new_values: новые значения (для create/update)
        reason: причина изменения
    """
    log = AuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        old_json=old_values,
        new_json=new_values,
        reason=reason,
    )

    db.add(log)
    await db.flush()
