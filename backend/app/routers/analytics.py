from statistics import mean, median

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from ..auth import get_current_user
from ..db import get_db
from ..helpers import (
    actor_key,
    basic_stats,
    rating_info,
    ratings_map,
    reaction_map,
)
from ..models import Comment, Event, Instruction

router = APIRouter(tags=["analytics"])


@router.get("/instructions/{instruction_id}/analytics")
def instruction_analytics(
    instruction_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    item = (
        db.query(Instruction)
        .options(
            selectinload(Instruction.steps),
            selectinload(Instruction.author),
        )
        .filter(Instruction.id == instruction_id)
        .first()
    )
    if not item:
        raise HTTPException(404, "Инструкция не найдена")
    if item.author_id != user.id:
        raise HTTPException(403, "Только автор видит аналитику")

    events = db.query(Event).filter(Event.instruction_id == item.id).all()
    steps = sorted(item.steps, key=lambda step: step.position)
    data = {
        step.id: {
            "reached": set(),
            "completed": set(),
            "skipped": set(),
            "stuck": set(),
            "times": [],
        }
        for step in steps
    }
    starts = set()
    finishes = set()
    for event in events:
        actor = actor_key(event)
        if event.type == "instruction_start":
            starts.add(actor)
        elif event.type == "instruction_complete":
            finishes.add(actor)
        elif event.step_id in data:
            step_data = data[event.step_id]
            if event.type == "step_view":
                step_data["reached"].add(actor)
            elif event.type == "step_complete":
                step_data["completed"].add(actor)
                if event.duration_ms:
                    step_data["times"].append(event.duration_ms)
            elif event.type == "step_skip":
                step_data["skipped"].add(actor)
                if event.duration_ms:
                    step_data["times"].append(event.duration_ms)
            elif event.type == "step_stuck":
                step_data["stuck"].add(actor)

    comments = (
        db.query(Comment.step_id, func.count(Comment.id))
        .filter(Comment.instruction_id == item.id, Comment.step_id.isnot(None))
        .group_by(Comment.step_id)
        .all()
    )
    comment_counts = {step_id: count for step_id, count in comments}
    suggestions = (
        db.query(Comment.step_id, func.count(Comment.id))
        .filter(
            Comment.instruction_id == item.id,
            Comment.kind == "suggestion",
            Comment.resolved.is_(False),
        )
        .group_by(Comment.step_id)
        .all()
    )
    suggestion_counts = {
        step_id: count for step_id, count in suggestions if step_id
    }
    reactions = reaction_map(db, "step", [step.id for step in steps])

    rows = []
    for step in steps:
        step_data = data[step.id]
        reached = len(step_data["reached"])
        completed = len(step_data["completed"])
        dropoff = max(reached - completed, 0)
        dropoff_pct = round(dropoff / reached * 100, 1) if reached else 0
        times = step_data["times"]
        reaction = reactions.get(step.id, {"likes": 0, "dislikes": 0})
        rows.append(
            {
                "step_id": step.id,
                "position": step.position,
                "title": step.title,
                "reached": reached,
                "completed": completed,
                "skipped": len(step_data["skipped"]),
                "stuck": len(step_data["stuck"]),
                "dropoff": dropoff,
                "dropoff_pct": dropoff_pct,
                "avg_seconds": round(mean(times) / 1000, 1) if times else 0,
                "median_seconds": round(median(times) / 1000, 1) if times else 0,
                "comments": comment_counts.get(step.id, 0),
                "suggestions": suggestion_counts.get(step.id, 0),
                "likes": reaction["likes"],
                "dislikes": reaction["dislikes"],
            }
        )

    candidates = [row for row in rows if row["reached"] >= 3] or rows
    bottleneck = (
        max(candidates, key=lambda row: row["dropoff_pct"]) if candidates else None
    )
    if bottleneck and bottleneck["dropoff_pct"] <= 0:
        bottleneck = None

    avg, count, score = rating_info(db, item.id)
    forks = (
        db.query(Instruction)
        .options(selectinload(Instruction.author))
        .filter(
            Instruction.forked_from_id == item.id,
            Instruction.status == "published",
        )
        .order_by(Instruction.created_at.desc())
        .all()
    )
    fork_ratings = ratings_map(db, [fork.id for fork in forks])
    fork_rows = []
    for fork in forks:
        stats = basic_stats(db, fork.id)
        fork_avg, fork_count, _ = fork_ratings.get(fork.id, (0, 0, 0))
        fork_rows.append(
            {
                "id": fork.id,
                "title": fork.title,
                "author": fork.author.name,
                "rating_avg": fork_avg,
                "rating_count": fork_count,
                "completion_rate": stats["completion_rate"],
                "starts": stats["starts"],
            }
        )

    open_suggestions = (
        db.query(Comment)
        .options(selectinload(Comment.user), selectinload(Comment.step))
        .filter(
            Comment.instruction_id == item.id,
            Comment.kind == "suggestion",
            Comment.resolved.is_(False),
        )
        .order_by(Comment.created_at.desc())
        .all()
    )

    start_count = len(starts)
    finish_count = len(finishes)
    return {
        "instruction": {
            "id": item.id,
            "title": item.title,
            "status": item.status,
            "views": item.views,
        },
        "starts": start_count,
        "finishes": finish_count,
        "completion_rate": (
            round(finish_count / start_count * 100, 1) if start_count else 0
        ),
        "rating_avg": avg,
        "rating_count": count,
        "score": score,
        "bottleneck_step_id": bottleneck["step_id"] if bottleneck else None,
        "bottleneck_title": bottleneck["title"] if bottleneck else None,
        "steps": rows,
        "forks": fork_rows,
        "suggestions": [
            {
                "id": comment.id,
                "body": comment.body,
                "user": comment.user.name,
                "step_id": comment.step_id,
                "step_title": comment.step.title if comment.step else None,
                "created_at": comment.created_at,
            }
            for comment in open_suggestions
        ],
    }


@router.get("/me/analytics")
def my_analytics(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    items = (
        db.query(Instruction)
        .options(selectinload(Instruction.steps))
        .filter(Instruction.author_id == user.id)
        .order_by(Instruction.created_at.desc())
        .all()
    )
    ratings = ratings_map(db, [item.id for item in items])
    total_starts = 0
    total_finishes = 0
    rows = []
    for item in items:
        stats = basic_stats(db, item.id)
        avg, count, score = ratings.get(item.id, (0, 0, 0))
        total_starts += stats["starts"]
        total_finishes += stats["finishes"]
        rows.append(
            {
                "id": item.id,
                "title": item.title,
                "status": item.status,
                "views": item.views,
                "starts": stats["starts"],
                "finishes": stats["finishes"],
                "completion_rate": stats["completion_rate"],
                "rating_avg": avg,
                "rating_count": count,
                "score": score,
            }
        )
    rows.sort(key=lambda row: row["starts"], reverse=True)
    return {
        "instructions": len(items),
        "starts": total_starts,
        "finishes": total_finishes,
        "completion_rate": (
            round(total_finishes / total_starts * 100, 1) if total_starts else 0
        ),
        "items": rows,
    }
