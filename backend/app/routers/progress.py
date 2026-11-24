from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..auth import get_current_user, get_optional_user, get_session_id
from ..db import get_db
from ..models import Event, Instruction, Step, StepProgress

router = APIRouter(tags=["progress"])

ALLOWED = {
    "instruction_start",
    "step_view",
    "step_complete",
    "step_skip",
    "step_stuck",
    "instruction_complete",
}


def upsert_progress(
    db: Session,
    session_id: str,
    user_id: int | None,
    instruction_id: int,
    step_id: int,
    status: str,
    time_ms: int,
):
    row = (
        db.query(StepProgress)
        .filter(StepProgress.session_id == session_id, StepProgress.step_id == step_id)
        .first()
    )
    if row:
        if row.status == "completed" and status == "viewed":
            return
        row.status = status
        row.time_ms = max(time_ms or 0, row.time_ms or 0)
        if user_id:
            row.user_id = user_id
        return
    db.add(
        StepProgress(
            session_id=session_id,
            user_id=user_id,
            instruction_id=instruction_id,
            step_id=step_id,
            status=status,
            time_ms=max(time_ms or 0, 0),
        )
    )


@router.post("/events")
def add_event(
    data: dict,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_optional_user),
):
    event_type = data.get("type")
    if event_type not in ALLOWED:
        raise HTTPException(400, "Неизвестное событие")
    try:
        instruction_id = int(data.get("instruction_id"))
    except (TypeError, ValueError):
        raise HTTPException(400, "Нет инструкции")
    instruction = db.get(Instruction, instruction_id)
    if not instruction:
        raise HTTPException(404, "Инструкция не найдена")

    step_id = data.get("step_id")
    step_id = int(step_id) if step_id else None
    if step_id:
        step = db.get(Step, step_id)
        if not step or step.instruction_id != instruction.id:
            raise HTTPException(400, "Шаг не из этой инструкции")

    duration = max(0, min(int(data.get("duration_ms") or 0), 3600000))
    session_id = get_session_id(request)
    user_id = user.id if user else None
    db.add(
        Event(
            session_id=session_id,
            user_id=user_id,
            instruction_id=instruction.id,
            step_id=step_id,
            type=event_type,
            duration_ms=duration,
        )
    )
    if step_id and event_type in {"step_view", "step_complete", "step_skip", "step_stuck"}:
        status = {
            "step_view": "viewed",
            "step_complete": "completed",
            "step_skip": "skipped",
            "step_stuck": "stuck",
        }[event_type]
        upsert_progress(
            db,
            session_id,
            user_id,
            instruction.id,
            step_id,
            status,
            duration,
        )
    db.commit()
    return {"ok": True}


@router.get("/progress/{instruction_id}")
def get_progress(
    instruction_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_optional_user),
):
    instruction = db.get(Instruction, instruction_id)
    if not instruction:
        raise HTTPException(404, "Инструкция не найдена")
    session_id = get_session_id(request)
    query = db.query(StepProgress).filter(
        StepProgress.instruction_id == instruction_id
    )
    if user:
        query = query.filter(StepProgress.user_id == user.id)
    else:
        query = query.filter(StepProgress.session_id == session_id)

    priority = {"viewed": 1, "stuck": 2, "skipped": 3, "completed": 4}
    state = {}
    for row in query.all():
        current = state.get(row.step_id)
        if not current or priority.get(row.status, 0) > priority.get(current, 0):
            state[row.step_id] = row.status

    steps = sorted(instruction.steps, key=lambda step: step.position)
    completed = [step_id for step_id, status in state.items() if status == "completed"]
    current_step = next(
        (step.id for step in steps if step.id not in completed),
        None,
    )

    finish_query = db.query(Event).filter(
        Event.instruction_id == instruction_id,
        Event.type == "instruction_complete",
    )
    if user:
        finish_query = finish_query.filter(Event.user_id == user.id)
    else:
        finish_query = finish_query.filter(Event.session_id == session_id)
    finished = finish_query.first() is not None or (
        bool(steps) and len(completed) >= len(steps)
    )
    return {
        "completed_step_ids": completed,
        "current_step_id": current_step,
        "finished": finished,
        "total_steps": len(steps),
        "completed_count": len(completed),
    }


@router.post("/progress/claim")
def claim_progress(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    session_id = get_session_id(request)
    db.query(StepProgress).filter(
        StepProgress.session_id == session_id,
        StepProgress.user_id.is_(None),
    ).update({StepProgress.user_id: user.id}, synchronize_session=False)
    db.query(Event).filter(
        Event.session_id == session_id,
        Event.user_id.is_(None),
    ).update({Event.user_id: user.id}, synchronize_session=False)
    db.commit()
    return {"ok": True}


@router.get("/me/progress")
def my_progress(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    rows = (
        db.query(StepProgress)
        .filter(StepProgress.user_id == user.id)
        .all()
    )
    grouped = {}
    for row in rows:
        data = grouped.setdefault(
            row.instruction_id,
            {"completed": set(), "last_at": row.updated_at or datetime.utcnow()},
        )
        if row.status == "completed":
            data["completed"].add(row.step_id)
        if row.updated_at and row.updated_at > data["last_at"]:
            data["last_at"] = row.updated_at

    instruction_ids = list(grouped.keys())
    instructions = (
        db.query(Instruction)
        .filter(Instruction.id.in_(instruction_ids))
        .all()
        if instruction_ids
        else []
    )
    items = []
    for instruction in instructions:
        data = grouped[instruction.id]
        total = len(instruction.steps)
        completed = len(data["completed"])
        items.append(
            {
                "instruction_id": instruction.id,
                "title": instruction.title,
                "completed": completed,
                "total": total,
                "percent": round(completed / total * 100) if total else 0,
                "finished": total > 0 and completed >= total,
                "last_at": data["last_at"],
            }
        )
    items.sort(key=lambda item: item["last_at"], reverse=True)
    return {"items": items}
