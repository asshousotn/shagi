import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from ..ai import chat, extract_json
from ..auth import get_current_user, get_optional_user, get_voter_key
from ..db import get_db
from ..helpers import (
    ZERO_STATS,
    attach_images,
    create_version,
    delete_instruction,
    instruction_detail,
    instruction_list_item,
    notify,
    purge_attachments,
    ratings_map,
    reaction_map,
    set_tags,
    sync_steps,
)
from ..models import Category, Comment, Event, Instruction, InstructionVersion, Step, Tag
from ..schemas import CoachApplyIn, CoachIn, InstructionDetail, InstructionIn, VersionOut
from ..search import rebuild, search

router = APIRouter(tags=["instructions"])

ARGS = (
    selectinload(Instruction.steps),
    selectinload(Instruction.author),
    selectinload(Instruction.category),
    selectinload(Instruction.tags),
)


def load_instruction(db: Session, instruction_id: int):
    return (
        db.query(Instruction)
        .options(*ARGS)
        .filter(Instruction.id == instruction_id)
        .first()
    )


def ensure_category(db: Session, category_id: int | None):
    if category_id and not db.get(Category, category_id):
        raise HTTPException(400, "Категория не найдена")


def own_instruction(db: Session, instruction_id: int, user):
    item = load_instruction(db, instruction_id)
    if not item:
        raise HTTPException(404, "Инструкция не найдена")
    if item.author_id != user.id:
        raise HTTPException(403, "Это не ваша инструкция")
    return item


def saved_detail(db: Session, instruction_id: int, user, reindex=True):
    db.commit()
    item = load_instruction(db, instruction_id)
    if reindex:
        rebuild(db)
    return instruction_detail(db, item, user, f"u:{user.id}")


@router.get("/instructions")
def list_instructions(
    q: str = "",
    category: int | None = None,
    difficulty: str | None = None,
    tag: str | None = None,
    sort: str = "new",
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Instruction)
        .options(*ARGS)
        .filter(Instruction.status == "published")
    )
    if category:
        query = query.filter(Instruction.category_id == category)
    if difficulty:
        query = query.filter(Instruction.difficulty == difficulty)
    if tag:
        query = query.join(Instruction.tags).filter(Tag.name == tag.lower())

    if q.strip():
        ids = search(db, q)
        if not ids:
            return {"items": [], "total": 0, "page": page, "pages": 0}
        items = query.filter(Instruction.id.in_(ids)).all()
        order = {instruction_id: index for index, instruction_id in enumerate(ids)}
        items.sort(key=lambda item: order.get(item.id, 9999))
        total = len(items)
        start = (page - 1) * page_size
        items = items[start : start + page_size]
    else:
        if sort == "rating":
            items = query.all()
            ratings = ratings_map(db, [item.id for item in items])
            items.sort(
                key=lambda item: ratings.get(item.id, (0, 0, 0))[2],
                reverse=True,
            )
            total = len(items)
            start = (page - 1) * page_size
            items = items[start : start + page_size]
        elif sort == "popular":
            query = query.order_by(Instruction.views.desc(), Instruction.created_at.desc())
            total = query.count()
            items = query.offset((page - 1) * page_size).limit(page_size).all()
        else:
            query = query.order_by(Instruction.created_at.desc())
            total = query.count()
            items = query.offset((page - 1) * page_size).limit(page_size).all()

    ids = [item.id for item in items]
    ratings = ratings_map(db, ids)
    reactions = reaction_map(db, "instruction", ids)
    payload = [instruction_list_item(db, item, ratings, reactions, ZERO_STATS) for item in items]
    return {
        "items": payload,
        "total": total,
        "page": page,
        "pages": (total + page_size - 1) // page_size if total else 0,
    }


@router.get("/me/instructions")
def my_instructions(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    items = (
        db.query(Instruction)
        .options(*ARGS)
        .filter(Instruction.author_id == user.id)
        .order_by(Instruction.created_at.desc())
        .all()
    )
    ids = [item.id for item in items]
    ratings = ratings_map(db, ids)
    reactions = reaction_map(db, "instruction", ids)
    return {
        "items": [instruction_list_item(db, item, ratings, reactions) for item in items]
    }


@router.get("/expert/queue")
def expert_queue(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if user.role != "expert":
        raise HTTPException(403, "Только для экспертов")
    items = (
        db.query(Instruction)
        .options(*ARGS)
        .filter(Instruction.status == "published", Instruction.verified_at.is_(None))
        .order_by(Instruction.created_at.desc())
        .all()
    )
    ids = [item.id for item in items]
    ratings = ratings_map(db, ids)
    reactions = reaction_map(db, "instruction", ids)
    return {
        "items": [instruction_list_item(db, item, ratings, reactions, ZERO_STATS) for item in items]
    }


@router.get("/instructions/{instruction_id}", response_model=InstructionDetail)
def get_instruction(
    instruction_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_optional_user),
    voter: str = Depends(get_voter_key),
):
    item = load_instruction(db, instruction_id)
    if not item:
        raise HTTPException(404, "Инструкция не найдена")
    if item.status != "published" and (not user or user.id != item.author_id):
        raise HTTPException(404, "Инструкция не найдена")
    if item.status == "published" and (not user or user.id != item.author_id):
        item.views += 1
        db.commit()
        db.refresh(item)
    return instruction_detail(db, item, user, voter)


@router.post("/instructions", response_model=InstructionDetail)
def create_instruction(
    data: InstructionIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    ensure_category(db, data.category_id)
    item = Instruction(
        title=data.title.strip(),
        summary=data.summary.strip(),
        category_id=data.category_id,
        author_id=user.id,
        difficulty=data.difficulty,
        minutes=data.minutes,
        cover_url=data.cover_url.strip(),
        status="draft",
    )
    db.add(item)
    db.flush()
    sync_steps(db, item, data.steps)
    set_tags(db, item, data.tags)
    purge_attachments(db, "instruction", item.id)
    attach_images(db, "instruction", item.id, data.images)
    return saved_detail(db, item.id, user)


@router.patch("/instructions/{instruction_id}", response_model=InstructionDetail)
def update_instruction(
    instruction_id: int,
    data: InstructionIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    item = own_instruction(db, instruction_id, user)
    ensure_category(db, data.category_id)
    if data.difficulty not in {"easy", "medium", "hard"}:
        raise HTTPException(400, "Плохая сложность")
    item.title = data.title.strip()
    item.summary = data.summary.strip()
    item.category_id = data.category_id
    item.difficulty = data.difficulty
    item.minutes = data.minutes
    item.cover_url = data.cover_url.strip()
    sync_steps(db, item, data.steps)
    set_tags(db, item, data.tags)
    purge_attachments(db, "instruction", item.id)
    attach_images(db, "instruction", item.id, data.images)
    return saved_detail(db, instruction_id, user)


@router.delete("/instructions/{instruction_id}")
def remove_instruction(
    instruction_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    item = own_instruction(db, instruction_id, user)
    delete_instruction(db, item)
    db.commit()
    rebuild(db)
    return {"ok": True}


@router.post("/instructions/{instruction_id}/publish", response_model=InstructionDetail)
def publish_instruction(
    instruction_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    item = own_instruction(db, instruction_id, user)
    if not item.steps:
        raise HTTPException(400, "Добавьте хотя бы один шаг")
    item.status = "published"
    if not item.published_at:
        item.published_at = datetime.utcnow()
    return saved_detail(db, instruction_id, user)


@router.post("/instructions/{instruction_id}/unpublish", response_model=InstructionDetail)
def unpublish_instruction(
    instruction_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    item = own_instruction(db, instruction_id, user)
    item.status = "draft"
    return saved_detail(db, instruction_id, user)


@router.post("/instructions/{instruction_id}/fork", response_model=InstructionDetail)
def fork_instruction(
    instruction_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    original = load_instruction(db, instruction_id)
    if not original or original.status != "published":
        raise HTTPException(404, "Инструкция не найдена")
    copy = Instruction(
        title=original.title,
        summary=original.summary,
        category_id=original.category_id,
        author_id=user.id,
        status="draft",
        difficulty=original.difficulty,
        minutes=original.minutes,
        cover_url=original.cover_url,
        forked_from_id=original.id,
    )
    db.add(copy)
    db.flush()
    for step in original.steps:
        db.add(
            Step(
                instruction_id=copy.id,
                position=step.position,
                title=step.title,
                body=step.body,
                image_url=step.image_url,
            )
        )
    copy.tags = list(original.tags)
    notify(
        db,
        original.author_id,
        "fork_created",
        {
            "instruction_id": original.id,
            "instruction_title": original.title,
            "fork_id": copy.id,
            "user": user.name,
        },
    )
    return saved_detail(db, copy.id, user)


@router.get("/instructions/{instruction_id}/forks")
def instruction_forks(instruction_id: int, db: Session = Depends(get_db)):
    items = (
        db.query(Instruction)
        .options(*ARGS)
        .filter(
            Instruction.forked_from_id == instruction_id,
            Instruction.status == "published",
        )
        .all()
    )
    ids = [item.id for item in items]
    ratings = ratings_map(db, ids)
    reactions = reaction_map(db, "instruction", ids)
    return {
        "items": [instruction_list_item(db, item, ratings, reactions) for item in items]
    }


@router.post("/instructions/{instruction_id}/verify", response_model=InstructionDetail)
def verify_instruction(
    instruction_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if user.role != "expert":
        raise HTTPException(403, "Только для экспертов")
    item = load_instruction(db, instruction_id)
    if not item or item.status != "published":
        raise HTTPException(404, "Инструкция не найдена")
    item.verified_at = datetime.utcnow()
    item.verified_by = user.id
    if item.author_id != user.id:
        notify(
            db,
            item.author_id,
            "verified",
            {
                "instruction_id": item.id,
                "instruction_title": item.title,
                "expert": user.name,
            },
        )
    return saved_detail(db, instruction_id, user, reindex=False)


@router.delete("/instructions/{instruction_id}/verify", response_model=InstructionDetail)
def unverify_instruction(
    instruction_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if user.role != "expert":
        raise HTTPException(403, "Только для экспертов")
    item = load_instruction(db, instruction_id)
    if not item:
        raise HTTPException(404, "Инструкция не найдена")
    item.verified_at = None
    item.verified_by = None
    return saved_detail(db, instruction_id, user, reindex=False)


@router.get("/instructions/{instruction_id}/versions", response_model=list[VersionOut])
def list_versions(
    instruction_id: int,
    db: Session = Depends(get_db),
):
    instruction = db.get(Instruction, instruction_id)
    if not instruction or instruction.status != "published":
        raise HTTPException(404, "Инструкция не найдена")
    versions = (
        db.query(InstructionVersion)
        .options(selectinload(InstructionVersion.author))
        .filter(InstructionVersion.instruction_id == instruction_id)
        .order_by(InstructionVersion.number.desc())
        .all()
    )
    return [
        {
            "id": version.id,
            "number": version.number,
            "message": version.message or "",
            "created_at": version.created_at,
            "author": (
                {
                    "id": version.author.id,
                    "name": version.author.name,
                    "role": version.author.role,
                }
                if version.author
                else None
            ),
            "steps": json.loads(version.steps_json),
        }
        for version in versions
    ]


@router.post("/instructions/{instruction_id}/versions/{version_id}/rollback", response_model=InstructionDetail)
def rollback_version(
    instruction_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    item = own_instruction(db, instruction_id, user)
    version = (
        db.query(InstructionVersion)
        .filter(
            InstructionVersion.id == version_id,
            InstructionVersion.instruction_id == instruction_id,
        )
        .first()
    )
    if not version:
        raise HTTPException(404, "Версия не найдена")
    steps = json.loads(version.steps_json)
    for step in list(item.steps):
        db.delete(step)
    db.flush()
    for step_data in steps:
        db.add(
            Step(
                instruction_id=item.id,
                position=step_data.get("position", 0),
                title=step_data.get("title", ""),
                body=step_data.get("body", ""),
                image_url=step_data.get("image_url", ""),
            )
        )
    create_version(db, item, user.id, f"Откат к версии {version.number}")
    return saved_detail(db, instruction_id, user)


@router.post("/instructions/{instruction_id}/ai-coach")
async def ai_coach(
    instruction_id: int,
    data: CoachIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    item = own_instruction(db, instruction_id, user)
    step = db.get(Step, data.step_id)
    if not step or step.instruction_id != item.id:
        raise HTTPException(404, "Шаг не найден")
    comments = (
        db.query(Comment)
        .filter(Comment.instruction_id == item.id, Comment.step_id == step.id)
        .limit(10)
        .all()
    )
    comment_text = "\n".join(f"- {comment.body}" for comment in comments) or "нет комментариев"
    stats = (
        db.query(Event)
        .filter(Event.instruction_id == item.id, Event.step_id == step.id)
        .all()
    )
    reached = len({f"s:{event.session_id}" if not event.user_id else f"u:{event.user_id}" for event in stats if event.type == "step_view"})
    completed = len({f"s:{event.session_id}" if not event.user_id else f"u:{event.user_id}" for event in stats if event.type == "step_complete"})
    stuck = sum(1 for event in stats if event.type == "step_stuck")
    prompt = (
        f"Инструкция: {item.title}\n"
        f"Шаг: {step.title}\n"
        f"Текст шага: {step.body}\n"
        f"Дошли: {reached}, завершили: {completed}, отметили «застрял»: {stuck}\n"
        f"Комментарии читателей:\n{comment_text}\n\n"
        "Объясни по-русски вероятные причины сложности и предложи переписанный текст шага. "
        'Верни JSON: {"causes": ["причина1", "причина2"], "rewrite": "новый текст"}'
    )
    system = "Ты pedagogical editor. Отвечай только JSON без пояснений."
    raw = await chat(prompt, system, json_mode=True, require_keys=("causes", "rewrite"))
    if not raw:
        return {
            "ai": False,
            "causes": ["Мало данных по шагу", "Проверьте фото и пример"],
            "rewrite": step.body,
        }
    data_obj = extract_json(raw, ("causes", "rewrite")) or {}
    return {
        "ai": True,
        "causes": data_obj.get("causes") or [],
        "rewrite": str(data_obj.get("rewrite") or step.body),
    }


@router.post("/instructions/{instruction_id}/ai-coach/apply", response_model=InstructionDetail)
async def apply_ai_coach(
    instruction_id: int,
    data: CoachApplyIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    item = own_instruction(db, instruction_id, user)
    step = db.get(Step, data.step_id)
    if not step or step.instruction_id != item.id:
        raise HTTPException(404, "Шаг не найден")
    step.body = data.body.strip()
    create_version(db, item, user.id, data.message or "Правка по подсказке ИИ")
    return saved_detail(db, instruction_id, user)
