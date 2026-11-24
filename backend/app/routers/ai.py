import time

from fastapi import APIRouter, Depends, HTTPException

from ..ai import generate_instruction, improve_text, suggest_tags
from ..auth import get_current_user
from ..schemas import AIInstructionIn, AIImproveIn, AITagsIn

router = APIRouter(prefix="/ai", tags=["ai"])
LAST_CALL = {}


def check_limit(user):
    now = time.monotonic()
    last = LAST_CALL.get(user.id, 0)
    if now - last < 2:
        raise HTTPException(429, "Слишком часто. Подождите 2 секунды")
    LAST_CALL[user.id] = now


@router.post("/instruction")
async def ai_instruction(
    data: AIInstructionIn,
    user=Depends(get_current_user),
):
    check_limit(user)
    return await generate_instruction(data.goal, data.audience, data.level)


@router.post("/improve")
async def ai_improve(
    data: AIImproveIn,
    user=Depends(get_current_user),
):
    check_limit(user)
    return await improve_text(data.text)


@router.post("/tags")
async def ai_tags(
    data: AITagsIn,
    user=Depends(get_current_user),
):
    check_limit(user)
    return await suggest_tags(data.title, data.summary)
