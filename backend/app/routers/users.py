import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from ..auth import get_current_user
from ..db import get_db
from ..helpers import ZERO_STATS, instruction_list_item, ratings_map, reaction_map
from ..models import Event, Instruction, Notification, User
from ..schemas import NotificationOut

router = APIRouter(tags=["users"])


@router.get("/users/{user_id}")
def public_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    items = (
        db.query(Instruction)
        .options(
            selectinload(Instruction.steps),
            selectinload(Instruction.author),
            selectinload(Instruction.category),
            selectinload(Instruction.tags),
        )
        .filter(Instruction.author_id == user.id, Instruction.status == "published")
        .order_by(Instruction.created_at.desc())
        .all()
    )
    ids = [item.id for item in items]
    ratings = ratings_map(db, ids)
    reactions = reaction_map(db, "instruction", ids)
    payload = [instruction_list_item(db, item, ratings, reactions, ZERO_STATS) for item in items]
    avg = (
        round(sum(item["rating_avg"] for item in payload) / len(payload), 1)
        if payload
        else 0
    )
    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "role": user.role,
            "bio": user.bio or "",
            "avatar_url": user.avatar_url or "",
        },
        "stats": {
            "instructions": len(payload),
            "views": sum(item["views"] for item in payload),
            "rating_avg": avg,
        },
        "instructions": payload,
    }


@router.get("/me/notifications", response_model=list[NotificationOut])
def my_notifications(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    rows = (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": row.id,
            "type": row.type,
            "payload": json.loads(row.payload_json or "{}"),
            "read_at": row.read_at,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.post("/me/notifications/{notification_id}/read", response_model=NotificationOut)
def read_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    row = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user.id)
        .first()
    )
    if not row:
        raise HTTPException(404, "Уведомление не найдено")
    row.read_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "type": row.type,
        "payload": json.loads(row.payload_json or "{}"),
        "read_at": row.read_at,
        "created_at": row.created_at,
    }


@router.get("/me/activity")
def my_activity(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    events = (
        db.query(Event)
        .filter(Event.user_id == user.id)
        .order_by(Event.created_at.desc())
        .limit(20)
        .all()
    )
    titles = {item.id: item.title for item in db.query(Instruction).all()}
    return {
        "items": [
            {
                "type": event.type,
                "instruction_id": event.instruction_id,
                "instruction_title": titles.get(event.instruction_id, "Инструкция"),
                "step_id": event.step_id,
                "created_at": event.created_at,
            }
            for event in events
        ]
    }
