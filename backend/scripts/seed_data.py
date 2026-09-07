"""Idempotent NEW_TZ catalogs. No people or bookings are added to the working database."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import (
    ExerciseCatalog,
    SkillCatalog,
    VerdictCatalog,
    InterventionReasonCatalog,
    ScoreFormulaVersion,
)

GROUND_SKILLS = [
    ("Управление автомобилем", 15),
    ("Чувство габаритов", 15),
    ("Маневрирование", 15),
    ("Парковка / точность остановки", 15),
    ("Экзаменационные упражнения площадки", 20),
    ("Безопасность и соблюдение алгоритма", 20),
]
CITY_SKILLS = [
    ("Управление автомобилем", 10),
    ("Наблюдение и контроль обстановки", 20),
    ("Перекрёстки и приоритет", 15),
    ("Перестроения и манёвры", 15),
    ("Скорость и дистанция", 10),
    ("Пешеходы / препятствия / безопасность", 15),
    ("Парковка в городе", 5),
    ("Прогнозирование опасности и выбор решения", 10),
]
GROUND_EXERCISES = [
    "Подготовка к движению",
    "Начало движения и остановка",
    "Руль и габариты",
    "Переключение передач",
    "Развороты",
    "Движение задним ходом",
    "Остановка в заданном месте",
    "Парковка / въезд в бокс",
    "Эстакада",
    "Змейка / ограниченный проезд",
    "Линия «Стоп»",
    "Парковка между автомобилями",
    "Экстренное торможение",
    "Экзаменационные элементы",
    "Контрольная проверка",
    "Другое",
]
CITY_EXERCISES = [
    "Включение в поток",
    "Повороты",
    "Нерегулируемые перекрёстки",
    "Регулируемые перекрёстки",
    "Приоритет / уступить дорогу",
    "Перестроения",
    "Многорядное движение",
    "Скорость и дистанция",
    "Пешеходные переходы",
    "Интенсивный поток",
    "Дворы и ограниченные проезды",
    "Парковка в городе",
    "Самостоятельный маршрут",
    "Подъёмы / спуски",
    "Сложные условия",
    "Контрольная поездка",
    "Другое",
]


async def seed_exercises(session):
    for context, names, section in [
        ("Учебная площадка", GROUND_EXERCISES, "Раздел 2 — обучение на автодроме"),
        ("Город", CITY_EXERCISES, "Раздел 3–4 — городские маршруты"),
    ]:
        if (
            await session.execute(
                select(ExerciseCatalog.id)
                .where(ExerciseCatalog.context == context)
                .limit(1)
            )
        ).scalar():
            continue
        session.add_all(
            [
                ExerciseCatalog(
                    context=context,
                    short_name=name,
                    official_name=name,
                    paper_section=section,
                    sort_order=i,
                )
                for i, name in enumerate(names)
            ]
        )
    await session.flush()


async def seed_skills(session):
    for context, skills in [
        ("Учебная площадка", GROUND_SKILLS),
        ("Город", CITY_SKILLS),
    ]:
        if (
            await session.execute(
                select(SkillCatalog.id).where(SkillCatalog.context == context).limit(1)
            )
        ).scalar():
            continue
        session.add_all(
            [
                SkillCatalog(
                    context=context,
                    name=name,
                    weight=weight,
                    is_core=True,
                    sort_order=i,
                    version=1,
                )
                for i, (name, weight) in enumerate(skills)
            ]
        )
    await session.flush()


async def seed_verdicts(session):
    if not (await session.execute(select(VerdictCatalog.id).limit(1))).scalar():
        session.add_all(
            [
                VerdictCatalog(name=name, sort_order=i)
                for i, name in enumerate(
                    [
                        "Прогресс хороший",
                        "Прогресс есть, продолжить отработку",
                        "Требуется повторение текущего этапа",
                        "Есть серьёзные ошибки / требуется внимание",
                    ]
                )
            ]
        )
    await session.flush()


async def seed_intervention_reasons(session):
    if not (
        await session.execute(select(InterventionReasonCatalog.id).limit(1))
    ).scalar():
        for context in ("Учебная площадка", "Город"):
            session.add_all(
                [
                    InterventionReasonCatalog(
                        context=context, name=name, criticality=criticality
                    )
                    for name, criticality in [
                        ("Руль", "high"),
                        ("Тормоз", "high"),
                        ("Не уступил дорогу", "high"),
                        ("Пешеход / препятствие", "critical"),
                        ("Потеря контроля", "critical"),
                        ("Опасное перестроение", "critical"),
                        ("Другое", "medium"),
                    ]
                ]
            )
    await session.flush()


async def seed_formula_version(session):
    if not (
        await session.execute(select(ScoreFormulaVersion.version).limit(1))
    ).scalar():
        from app.api.admin.catalogs import formula_version

        await formula_version(session)


async def seed_all(session):
    await seed_exercises(session)
    await seed_skills(session)
    await seed_verdicts(session)
    await seed_intervention_reasons(session)
    await seed_formula_version(session)
    await session.commit()


async def main():
    async with AsyncSessionLocal() as session:
        await seed_all(session)
    print("Справочники готовы. Существующие записи сохранены.")


if __name__ == "__main__":
    asyncio.run(main())
