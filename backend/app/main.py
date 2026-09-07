from app.core.time import utc_now

"""Главный файл FastAPI приложения"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from app.core.rate_limit import RateLimitMiddleware

from app.core.config import settings
from app.api.instructor.router import router as instructor_router
from app.api.admin.bookings import router as admin_bookings_router
from app.api.admin.auth import router as admin_auth_router
from app.api.admin.instructors import router as admin_instructors_router
from app.api.admin.clients import router as admin_clients_router
from app.api.admin.ai_drafts import router as admin_ai_drafts_router
from app.api.admin.attention_flags import router as admin_attention_flags_router
from app.api.telegram import router as telegram_router
from app.api.admin.governance import router as governance_router
from app.api.admin.catalogs import router as catalogs_router

app = FastAPI(
    title="Instructor Mini App API",
    description="Backend для Telegram Mini App инструкторов автошколы",
    version="1.0.0",
    debug=settings.ENABLE_DEBUG,
)

# CORS
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_MINI_APP_URL, settings.FRONTEND_ADMIN_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse(
        status_code=409,
        content={
            "detail": "Данные уже изменены или связаны с другой записью. Обновите страницу и повторите действие"
        },
    )


@app.get("/")
async def root():
    """Health check"""
    return {"status": "ok", "service": "instructor-api", "version": "1.0.0"}


@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Health check endpoint for both legacy and API monitoring URLs."""
    return {"status": "healthy", "timestamp": utc_now().isoformat()}


# Подключаем роутеры
app.include_router(instructor_router, prefix="/api/instructor", tags=["Instructor"])
app.include_router(admin_auth_router, prefix="/admin/auth", tags=["Admin Auth"])
app.include_router(admin_bookings_router, prefix="/admin", tags=["Admin"])
app.include_router(admin_instructors_router, prefix="/admin", tags=["Admin"])
app.include_router(admin_clients_router, prefix="/admin", tags=["Admin"])
app.include_router(admin_ai_drafts_router, prefix="/admin", tags=["Admin AI"])
app.include_router(admin_attention_flags_router, prefix="/admin", tags=["Admin Flags"])
app.include_router(telegram_router, prefix="/api/telegram", tags=["Telegram"])
app.include_router(governance_router, prefix="/admin", tags=["Admin Control"])
app.include_router(catalogs_router, prefix="/admin", tags=["Admin Catalogs"])
