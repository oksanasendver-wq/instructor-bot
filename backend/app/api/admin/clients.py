"""CRUD для клиентов (администратор)"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from app.core.validation import PersonInput
from app.services.client_profile import client_profile
from app.services.audit import audit_log

from app.core.database import get_db
from app.models import Client, Booking, LessonReport
from app.api.admin.dependencies import get_current_admin

router = APIRouter()


class ClientCreateRequest(PersonInput):
    """Создание клиента"""

    notes_internal: Optional[str] = Field(default=None, max_length=3000)


class ClientResponse(BaseModel):
    """Ответ с клиентом"""

    id: int
    full_name: str
    phone: str
    notes_internal: Optional[str]
    is_archived: bool = False
    created_at: str

    class Config:
        from_attributes = True


@router.post("/clients", response_model=ClientResponse)
async def create_client(
    request: ClientCreateRequest,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Создать клиента"""
    client = Client(
        full_name=request.full_name,
        phone=request.phone,
        notes_internal=request.notes_internal,
    )

    db.add(client)
    await db.flush()
    await audit_log(
        db, "admin", 0, "client", client.id, "create", new_values=request.model_dump()
    )
    await db.commit()
    await db.refresh(client)

    return ClientResponse(
        id=client.id,
        full_name=client.full_name,
        phone=client.phone,
        notes_internal=client.notes_internal,
        is_archived=client.is_archived,
        created_at=client.created_at.isoformat(),
    )


@router.get("/clients", response_model=List[ClientResponse])
async def list_clients(
    search: Optional[str] = None,
    archived: bool = False,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Список всех клиентов"""
    query = select(Client).where(Client.is_archived.is_(archived))

    if search:
        query = query.where(Client.full_name.ilike(f"%{search}%"))

    query = query.order_by(Client.full_name)

    result = await db.execute(query)
    clients = result.scalars().all()

    return [
        ClientResponse(
            id=c.id,
            full_name=c.full_name,
            phone=c.phone,
            notes_internal=c.notes_internal,
            is_archived=c.is_archived,
            created_at=c.created_at.isoformat(),
        )
        for c in clients
    ]


@router.get("/clients/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: int,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Получить клиента"""
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    return ClientResponse(
        id=client.id,
        full_name=client.full_name,
        phone=client.phone,
        notes_internal=client.notes_internal,
        is_archived=client.is_archived,
        created_at=client.created_at.isoformat(),
    )


@router.patch("/clients/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: int,
    request: ClientCreateRequest,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Обновить клиента"""
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    client.full_name = request.full_name
    client.phone = request.phone
    client.notes_internal = request.notes_internal
    await audit_log(
        db, "admin", 0, "client", client.id, "update", new_values=request.model_dump()
    )

    await db.commit()
    await db.refresh(client)

    return ClientResponse(
        id=client.id,
        full_name=client.full_name,
        phone=client.phone,
        notes_internal=client.notes_internal,
        is_archived=client.is_archived,
        created_at=client.created_at.isoformat(),
    )


@router.delete("/clients/{client_id}")
async def delete_client(
    client_id: int,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Удалить клиента"""
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    await audit_log(
        db,
        "admin",
        0,
        "client",
        client.id,
        "delete",
        old_values={"full_name": client.full_name},
    )
    has_history = (
        await db.execute(
            select(LessonReport.id)
            .join(Booking)
            .where(Booking.client_id == client_id)
            .limit(1)
        )
    ).scalar_one_or_none()
    if has_history:
        client.is_archived = True
    else:
        await db.delete(client)
    await db.commit()

    return {"status": "ok", "message": "Client deleted"}


@router.get("/clients/{client_id}/profile")
async def get_profile(
    client_id: int,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    return await client_profile(db, client_id, admin=True)


@router.post("/clients/{client_id}/restore")
async def restore_client(
    client_id: int,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(404, "Клиент не найден")
    client.is_archived = False
    await audit_log(db, "admin", 0, "client", client_id, "restore")
    await db.commit()
    return {"status": "ok"}
