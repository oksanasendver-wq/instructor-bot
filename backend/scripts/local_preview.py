"""Isolated local preview server. Never import this module in a deployment."""

import os
import sys
import secrets
from pathlib import Path
from datetime import datetime, date, time, timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
LOCAL = ROOT / ".local"
LOCAL.mkdir(exist_ok=True)
database = LOCAL / ("preview-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".sqlite")
for key, value in {
    "DATABASE_URL": "sqlite+aiosqlite:///" + database.as_posix(),
    "SECRET_KEY": secrets.token_hex(32),
    "TELEGRAM_BOT_TOKEN": "123456789:local-preview-token",
    "TELEGRAM_WEBHOOK_SECRET": "local-preview-secret",
    "ADMIN_USERNAME": "local-admin",
    "ADMIN_PASSWORD": "instructor-local",
    "FRONTEND_MINI_APP_URL": "http://127.0.0.1:5173",
    "FRONTEND_ADMIN_URL": "http://127.0.0.1:5174",
    "GROQ_API_KEY": "",
    "NVIDIA_API_KEY": "",
    "TIMEZONE": "Asia/Almaty",
    "ENABLE_DEBUG": "false",
}.items():
    os.environ[key] = value
import hashlib, hmac, json, time as epoch
from urllib.parse import urlencode
from contextlib import asynccontextmanager
from fastapi import Request
from sqlalchemy import select
from app.main import app
from app.core.database import engine, Base, AsyncSessionLocal
from app.models import (
    Instructor,
    Client,
    Booking,
    LessonReport,
    ScoreSnapshot,
    SkillAssessment,
    Intervention,
    LessonExercise,
    SkillCatalog,
    ExerciseCatalog,
)
from app.services.score_engine import ScoreEngine
from app.core.time import utc_now
from app.services.attention_flag_manager import AttentionFlagManager
from scripts.seed_data import seed_all

clock = {"now": datetime.combine(date.today(), time(12))}
import app.core.time as times
import app.api.instructor.bookings as instructor_bookings
import app.api.admin.bookings as admin_bookings
import app.services.lifecycle as lifecycle
import app.services.access_control as access

for module in (times, instructor_bookings, admin_bookings, lifecycle, access):
    module.school_now = lambda: clock["now"]


async def seed():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        await seed_all(db)
        db.add_all(
            [
                Instructor(
                    id=1,
                    full_name="Алексей Иванов",
                    phone="+77001234567",
                    telegram_user_id=5123456789,
                    transmission="АКПП",
                ),
                Instructor(
                    id=2,
                    full_name="Дмитрий Орлов",
                    phone="+77001234568",
                    transmission="МКПП",
                ),
            ]
        )
        names = [
            "Иван Петров",
            "Мария Сидорова",
            "Артём Кузнецов",
            "Елена Смирнова",
            "Дмитрий Волков",
        ]
        db.add_all(
            [
                Client(id=i + 1, full_name=name, phone="+770012345" + str(70 + i))
                for i, name in enumerate(names)
            ]
        )
        await db.flush()
        today = clock["now"].date()
        for index in range(8):
            context = "Учебная площадка" if index % 2 == 0 else "Город"
            booking = Booking(
                client_id=2,
                instructor_id=1,
                date=today - timedelta(days=(8 - index) * 2),
                start_at=time(10),
                end_at=time(11),
                duration_minutes=60,
                context=context,
                transmission="АКПП",
                payment_type="пакет",
                amount_due=0,
                status="completed",
            )
            db.add(booking)
            await db.flush()
            report = LessonReport(
                booking_id=booking.id,
                instructor_id=1,
                context=context,
                overall_grade_1_5=4,
                autonomy_level="A3 — самостоятельно",
                quick_verdict="Прогресс есть, продолжить отработку",
                comment_internal="Увереннее держит траекторию. Продолжить работу с зеркалами перед перестроением.",
                created_at=utc_now() - timedelta(days=(8 - index) * 2),
                edited_until=utc_now() - timedelta(days=1),
            )
            db.add(report)
            await db.flush()
            skills = (
                (
                    await db.execute(
                        select(SkillCatalog).where(SkillCatalog.context == context)
                    )
                )
                .scalars()
                .all()
            )
            for j, skill in enumerate(skills):
                grade = min(4, 2 + index // 3 + (1 if j % 3 == 0 else 0))
                db.add(
                    SkillAssessment(
                        report_id=report.id,
                        skill_id=skill.id,
                        value_0_4=grade,
                        skill_version=skill.version,
                    )
                )
            exercise = (
                await db.execute(
                    select(ExerciseCatalog)
                    .where(ExerciseCatalog.context == context)
                    .limit(1)
                )
            ).scalar_one()
            db.add(
                LessonExercise(
                    report_id=report.id,
                    exercise_id=exercise.id,
                    official_name_snapshot=exercise.official_name,
                )
            )
            db.add(Intervention(report_id=report.id, type="нет", is_critical=False))
            await db.flush()
            await AttentionFlagManager(db).check_and_update_flags(2, context, report.id)
            await ScoreEngine(db).recalculate(2, report.id)
            snapshots = (
                (
                    await db.execute(
                        select(ScoreSnapshot).order_by(ScoreSnapshot.id.desc()).limit(3)
                    )
                )
                .scalars()
                .all()
            )
            for snapshot in snapshots:
                snapshot.calculated_at = report.created_at
        # Today's five appointments, including an active lesson and an arrival window.
        slots = [
            (1, 10, 11, "in_progress", "Учебная площадка"),
            (2, 12, 13, "planned", "Город"),
            (3, 14, 15, "planned", "Город"),
            (4, 16, 17, "planned", "Учебная площадка"),
            (5, 18, 19, "planned", "Город"),
        ]
        for cid, start, end, status, context in slots:
            db.add(
                Booking(
                    client_id=cid,
                    instructor_id=1,
                    date=today,
                    start_at=time(start),
                    end_at=time(end),
                    duration_minutes=60,
                    context=context,
                    transmission="АКПП",
                    status=status,
                    amount_due=10000 if cid == 2 else 0,
                    payment_type="наличные" if cid == 2 else "пакет",
                    payment_status="pending" if cid == 2 else "not_required",
                    arrived_at=utc_now() if status == "in_progress" else None,
                )
            )
        await db.commit()


@asynccontextmanager
async def lifespan(_):
    await seed()
    yield
    await engine.dispose()


app.router.lifespan_context = lifespan


@app.get("/__preview/session")
async def preview_session(request: Request):
    fields = {
        "auth_date": str(int(epoch.time())),
        "user": json.dumps(
            {"id": 5123456789, "first_name": "Алексей"}, ensure_ascii=False
        ),
    }
    secret = hmac.digest(
        b"WebAppData", os.environ["TELEGRAM_BOT_TOKEN"].encode(), "sha256"
    )
    fields["hash"] = hmac.new(
        secret,
        "\n".join(f"{k}={v}" for k, v in sorted(fields.items())).encode(),
        hashlib.sha256,
    ).hexdigest()
    return {"init_data": urlencode(fields), "school_time": clock["now"].isoformat()}


@app.post("/__preview/clock")
async def advance_clock(minutes: int = 0):
    clock["now"] += timedelta(minutes=minutes)
    return {"school_time": clock["now"].isoformat()}


if __name__ == "__main__":
    import uvicorn

    print(
        "Isolated preview. Admin: local-admin / instructor-local. School clock starts at 12:00."
    )
    uvicorn.run(app, host="127.0.0.1", port=8010, log_level="warning")
