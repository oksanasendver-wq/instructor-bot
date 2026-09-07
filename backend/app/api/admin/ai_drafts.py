"""Persisted AI drafts; approval is a separate human action."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import settings
from app.core.time import utc_iso
from app.models import AIDraft
from app.services.ai_provider import AIProvider
from app.services.client_profile import client_profile
from app.services.audit import audit_log
from app.api.admin.dependencies import get_current_admin

router = APIRouter()


def payload(draft):
    return {
        "id": draft.id,
        "generated_text": draft.generated_text,
        "provider": draft.provider,
        "model": draft.model,
        "created_at": utc_iso(draft.created_at),
    }


@router.post("/clients/{client_id}/ai-draft")
async def generate_ai_draft(
    client_id: int,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    profile = await client_profile(db, client_id, admin=True)
    reports = [r for r in profile["history"] if r["report_id"]]
    if not reports:
        raise HTTPException(422, "Сначала сохраните хотя бы один отчёт о занятии")
    provider = AIProvider.create(settings.AI_PROVIDER)
    if not provider.api_key:
        raise HTTPException(
            503,
            "ИИ не настроен. Добавьте ключ провайдера в настройки backend или напишите заключение вручную",
        )
    context = {
        "stats": profile["stats"],
        "scores": profile["scores"],
        "score_history": profile["score_history"][-30:],
        "reports": [
            {
                k: r[k]
                for k in (
                    "date",
                    "context",
                    "overall_grade",
                    "autonomy_level",
                    "quick_verdict",
                    "comment_internal",
                    "critical",
                    "interventions",
                )
            }
            for r in reports[:10]
        ],
        "flags": [
            {"reason": f["reason"], "active": f["active"]} for f in profile["flags"]
        ],
        "provider": provider.provider,
        "model": provider.model,
        "prompt_version": "v2",
    }
    input_hash = provider._calculate_hash(context)
    existing = (
        await db.execute(
            select(AIDraft)
            .where(AIDraft.client_id == client_id, AIDraft.input_hash == input_hash)
            .order_by(AIDraft.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing:
        return payload(existing)
    try:
        generation = await provider.generate_conclusion_draft(context)
    except Exception:
        raise HTTPException(
            502,
            "ИИ-провайдер сейчас недоступен. Повторите позже или оформите заключение вручную",
        )
    draft = AIDraft(
        client_id=client_id,
        provider=provider.provider,
        model=generation["model"],
        prompt_version="v2",
        input_hash=input_hash,
        generated_text=generation["text"],
    )
    db.add(draft)
    await db.flush()
    await audit_log(
        db,
        "admin",
        0,
        "ai_draft",
        draft.id,
        "generate",
        new_values={"client_id": client_id, "input_hash": input_hash},
    )
    await db.commit()
    return payload(draft)


@router.get("/clients/{client_id}/ai-drafts")
async def list_drafts(
    client_id: int,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    return [
        payload(d)
        for d in (
            await db.execute(
                select(AIDraft)
                .where(AIDraft.client_id == client_id)
                .order_by(AIDraft.id.desc())
            )
        ).scalars()
    ]
