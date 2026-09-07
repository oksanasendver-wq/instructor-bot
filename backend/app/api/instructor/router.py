"""Главный роутер для API инструктора"""

from fastapi import APIRouter

from .auth import router as auth_router
from .bookings import router as bookings_router
from .reports import router as reports_router
from .clients import router as clients_router
from .catalogs import router as catalogs_router

router = APIRouter()

# Подключаем суб-роутеры
router.include_router(auth_router, prefix="/auth", tags=["Auth"])
router.include_router(bookings_router, tags=["Instructor"])
router.include_router(reports_router, tags=["Reports"])
router.include_router(clients_router, tags=["Clients"])
router.include_router(catalogs_router, prefix="/catalogs", tags=["Catalogs"])
