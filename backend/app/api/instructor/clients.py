"""Client profiles are visible during a booking and permanently after attendance."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models import Client, Instructor, Booking, AccessGrant, AttentionFlag
from app.api.instructor.dependencies import get_current_instructor
from app.services.access_control import AccessControl
from app.services.client_profile import client_profile, flag_payload

router = APIRouter()


async def accessible_clients(db, instructor_id):
    ids = select(Booking.client_id).where(Booking.instructor_id == instructor_id)
    grants = select(AccessGrant.client_id).where(
        AccessGrant.instructor_id == instructor_id
    )
    clients = (
        (
            await db.execute(
                select(Client)
                .where(
                    Client.is_archived.is_(False),
                    or_(Client.id.in_(ids), Client.id.in_(grants)),
                )
                .order_by(Client.full_name)
            )
        )
        .scalars()
        .all()
    )
    access = AccessControl(db)
    return [c for c in clients if await access.can_access_client(instructor_id, c.id)]


@router.get("/clients")
async def list_clients(
    current_instructor: Instructor = Depends(get_current_instructor),
    db: AsyncSession = Depends(get_db),
):
    clients = await accessible_clients(db, current_instructor.id)
    flags = (
        (
            await db.execute(
                select(AttentionFlag).where(
                    AttentionFlag.client_id.in_([c.id for c in clients]),
                    AttentionFlag.active.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": c.id,
            "full_name": c.full_name,
            "phone": c.phone,
            "active_flags": sum(f.client_id == c.id for f in flags),
        }
        for c in clients
    ]


@router.get("/flags")
async def list_flags(
    current_instructor: Instructor = Depends(get_current_instructor),
    db: AsyncSession = Depends(get_db),
):
    clients = {c.id: c for c in await accessible_clients(db, current_instructor.id)}
    flags = (
        (
            await db.execute(
                select(AttentionFlag)
                .where(AttentionFlag.client_id.in_(clients))
                .order_by(AttentionFlag.active.desc(), AttentionFlag.opened_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [flag_payload(f, clients[f.client_id]) for f in flags]


async def authorized_profile(db, instructor, client_id):
    if not await AccessControl(db).can_access_client(instructor.id, client_id):
        raise HTTPException(403, "Ученик ещё не назначен вам или занятие уже закрыто")
    return await client_profile(db, client_id, instructor_id=instructor.id)


@router.get("/clients/{client_id}/profile")
async def get_client_profile(
    client_id: int,
    current_instructor: Instructor = Depends(get_current_instructor),
    db: AsyncSession = Depends(get_db),
):
    return await authorized_profile(db, current_instructor, client_id)


@router.get("/clients/{client_id}/history")
async def get_client_history(
    client_id: int,
    current_instructor: Instructor = Depends(get_current_instructor),
    db: AsyncSession = Depends(get_db),
):
    profile = await authorized_profile(db, current_instructor, client_id)
    return {"total": len(profile["history"]), "history": profile["history"]}


@router.get("/clients/{client_id}/scores")
async def get_client_scores(
    client_id: int,
    current_instructor: Instructor = Depends(get_current_instructor),
    db: AsyncSession = Depends(get_db),
):
    return (await authorized_profile(db, current_instructor, client_id))["scores"]
