"""CRUD для инструкторов (администратор)"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from app.core.validation import PersonInput
from app.models.instructor import TransmissionType
from app.services.audit import audit_log

from app.core.database import get_db
from app.models import Instructor
from app.api.admin.dependencies import get_current_admin

router = APIRouter()


class InstructorCreateRequest(PersonInput):
    """Создание инструктора"""

    transmission: Optional[TransmissionType] = None
    telegram_user_id: int | None = Field(default=None, gt=0, le=9007199254740991)
    is_active: bool = True


class InstructorResponse(BaseModel):
    """Ответ с инструктором"""

    id: int
    full_name: str
    phone: str
    telegram_user_id: Optional[int]
    transmission: Optional[str]
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


@router.post("/instructors", response_model=InstructorResponse)
async def create_instructor(
    request: InstructorCreateRequest,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Создать инструктора"""
    await check_unique(db, request)
    instructor = Instructor(
        full_name=request.full_name,
        phone=request.phone,
        transmission=request.transmission,
        is_active=request.is_active,
        telegram_user_id=request.telegram_user_id,
    )

    db.add(instructor)
    await db.flush()
    await audit_log(
        db,
        "admin",
        0,
        "instructor",
        instructor.id,
        "create",
        new_values=request.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(instructor)

    return InstructorResponse(
        id=instructor.id,
        full_name=instructor.full_name,
        phone=instructor.phone,
        telegram_user_id=instructor.telegram_user_id,
        transmission=instructor.transmission,
        is_active=instructor.is_active,
        created_at=instructor.created_at.isoformat(),
    )


@router.get("/instructors", response_model=List[InstructorResponse])
async def list_instructors(
    active_only: bool = False,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Список инструкторов"""
    query = select(Instructor)

    if active_only:
        query = query.where(Instructor.is_active == True)

    query = query.order_by(Instructor.full_name)

    result = await db.execute(query)
    instructors = result.scalars().all()

    return [
        InstructorResponse(
            id=i.id,
            full_name=i.full_name,
            phone=i.phone,
            telegram_user_id=i.telegram_user_id,
            transmission=i.transmission,
            is_active=i.is_active,
            created_at=i.created_at.isoformat(),
        )
        for i in instructors
    ]


@router.get("/instructors/{instructor_id}", response_model=InstructorResponse)
async def get_instructor(
    instructor_id: int,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Получить инструктора"""
    instructor = await db.get(Instructor, instructor_id)
    if not instructor:
        raise HTTPException(status_code=404, detail="Instructor not found")

    return InstructorResponse(
        id=instructor.id,
        full_name=instructor.full_name,
        phone=instructor.phone,
        telegram_user_id=instructor.telegram_user_id,
        transmission=instructor.transmission,
        is_active=instructor.is_active,
        created_at=instructor.created_at.isoformat(),
    )


@router.patch("/instructors/{instructor_id}", response_model=InstructorResponse)
async def update_instructor(
    instructor_id: int,
    request: InstructorCreateRequest,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Обновить инструктора"""
    instructor = await db.get(Instructor, instructor_id)
    if not instructor:
        raise HTTPException(status_code=404, detail="Instructor not found")

    await check_unique(db, request, instructor_id)
    instructor.full_name = request.full_name
    instructor.phone = request.phone
    instructor.transmission = request.transmission
    instructor.is_active = request.is_active
    instructor.telegram_user_id = request.telegram_user_id
    await audit_log(
        db,
        "admin",
        0,
        "instructor",
        instructor.id,
        "update",
        new_values=request.model_dump(mode="json"),
    )

    await db.commit()
    await db.refresh(instructor)

    return InstructorResponse(
        id=instructor.id,
        full_name=instructor.full_name,
        phone=instructor.phone,
        telegram_user_id=instructor.telegram_user_id,
        transmission=instructor.transmission,
        is_active=instructor.is_active,
        created_at=instructor.created_at.isoformat(),
    )


@router.delete("/instructors/{instructor_id}")
async def delete_instructor(
    instructor_id: int,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Деактивировать инструктора"""
    instructor = await db.get(Instructor, instructor_id)
    if not instructor:
        raise HTTPException(status_code=404, detail="Instructor not found")

    # Не удаляем физически, а деактивируем
    instructor.is_active = False
    await audit_log(db, "admin", 0, "instructor", instructor.id, "deactivate")
    await db.commit()

    return {"status": "ok", "message": "Instructor deactivated"}


async def check_unique(db, request, exclude_id=0):
    from sqlalchemy import or_

    conditions = [Instructor.phone == request.phone]
    if request.telegram_user_id:
        conditions.append(Instructor.telegram_user_id == request.telegram_user_id)
    if (
        await db.execute(
            select(Instructor.id)
            .where(Instructor.id != exclude_id, or_(*conditions))
            .limit(1)
        )
    ).scalar_one_or_none():
        raise HTTPException(
            409, "Инструктор с таким телефоном или Telegram ID уже существует"
        )
