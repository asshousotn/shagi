import json
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import (
    Attachment,
    Bookmark,
    Comment,
    Event,
    Instruction,
    InstructionVersion,
    Notification,
    Rating,
    Reaction,
    Step,
    StepProgress,
    Tag,
)


def rating_info(db: Session, instruction_id: int):
    avg, count = (
        db.query(func.avg(Rating.score), func.count(Rating.id))
        .filter(Rating.instruction_id == instruction_id)
        .one()
    )
    avg = float(avg or 0)
    count = int(count or 0)
    score = round((avg * count + 4 * 3) / (count + 3), 2) if count else 0
    return round(avg, 1), count, score


def ratings_map(db: Session, ids: list[int]):
    if not ids:
        return {}
    rows = (
        db.query(Rating.instruction_id, func.avg(Rating.score), func.count(Rating.id))
        .filter(Rating.instruction_id.in_(ids))
        .group_by(Rating.instruction_id)
        .all()
    )
    result = {}
    for instruction_id, avg, count in rows:
        avg = float(avg or 0)
        count = int(count or 0)
        score = round((avg * count + 4 * 3) / (count + 3), 2) if count else 0
        result[instruction_id] = (round(avg, 1), count, score)
    return result


def reaction_map(db: Session, target_type: str, ids: list[int]):
    result = {target_id: {"likes": 0, "dislikes": 0} for target_id in ids}
    if not ids:
        return result
    rows = (
        db.query(Reaction.target_id, Reaction.value, func.count(Reaction.id))
        .filter(Reaction.target_type == target_type, Reaction.target_id.in_(ids))
        .group_by(Reaction.target_id, Reaction.value)
        .all()
    )
    for target_id, value, count in rows:
        if value > 0:
            result[target_id]["likes"] = count
        else:
            result[target_id]["dislikes"] = count
    return result


def actor_key(event: Event) -> str:
    return f"u:{event.user_id}" if event.user_id else f"s:{event.session_id}"


ZERO_STATS = {"starts": 0, "finishes": 0, "completion_rate": 0}


def basic_stats(db: Session, instruction_id: int):
    events = db.query(Event).filter(Event.instruction_id == instruction_id).all()
    starts = set()
    finishes = set()
    for event in events:
        actor = actor_key(event)
        if event.type == "instruction_start":
            starts.add(actor)
        elif event.type == "instruction_complete":
            finishes.add(actor)
    rate = round(len(finishes) / len(starts) * 100, 1) if starts else 0
    return {"starts": len(starts), "finishes": len(finishes), "completion_rate": rate}


def instruction_list_item(db: Session, item: Instruction, ratings=None, reactions=None, stats=None):
    avg, count, score = (ratings or {}).get(item.id, (0, 0, 0))
    reaction = (reactions or {}).get(item.id, {"likes": 0, "dislikes": 0})
    stats = stats or basic_stats(db, item.id)
    return {
        "id": item.id,
        "title": item.title,
        "summary": item.summary or "",
        "author": {
            "id": item.author.id,
            "name": item.author.name,
            "role": item.author.role,
        },
        "category": (
            {"id": item.category.id, "name": item.category.name}
            if item.category
            else None
        ),
        "difficulty": item.difficulty,
        "minutes": item.minutes,
        "cover_url": item.cover_url or "",
        "status": item.status,
        "verified_at": item.verified_at,
        "forked_from_id": item.forked_from_id,
        "created_at": item.created_at,
        "rating_avg": avg,
        "rating_count": count,
        "score": score,
        "steps_count": len(item.steps),
        "views": item.views,
        "likes": reaction["likes"],
        "dislikes": reaction["dislikes"],
        "completion_rate": stats["completion_rate"],
        "starts": stats["starts"],
    }


def instruction_detail(db: Session, item: Instruction, user=None, voter: str | None = None):
    ratings = ratings_map(db, [item.id])
    reactions = reaction_map(db, "instruction", [item.id])
    stats = basic_stats(db, item.id)
    payload = instruction_list_item(db, item, ratings=ratings, reactions=reactions, stats=stats)

    step_reactions = reaction_map(db, "step", [step.id for step in item.steps])
    steps = []
    for step in item.steps:
        reaction = step_reactions.get(step.id, {"likes": 0, "dislikes": 0})
        steps.append(
            {
                "id": step.id,
                "position": step.position,
                "title": step.title,
                "body": step.body or "",
                "image_url": step.image_url or "",
                "images": attachments_for(db, "step", step.id),
                "likes": reaction["likes"],
                "dislikes": reaction["dislikes"],
            }
        )

    comments_count = db.query(Comment).filter(Comment.instruction_id == item.id).count()
    forks_count = (
        db.query(Instruction)
        .filter(Instruction.forked_from_id == item.id, Instruction.status == "published")
        .count()
    )
    my_rating = None
    if voter:
        rating = (
            db.query(Rating)
            .filter(Rating.instruction_id == item.id, Rating.voter_key == voter)
            .first()
        )
        my_rating = rating.score if rating else None
    bookmarked = False
    if user:
        bookmarked = (
            db.query(Bookmark)
            .filter(Bookmark.user_id == user.id, Bookmark.instruction_id == item.id)
            .first()
            is not None
        )

    payload.update(
        {
            "steps": steps,
            "images": attachments_for(db, "instruction", item.id),
            "tags": [{"id": tag.id, "name": tag.name} for tag in item.tags],
            "forks_count": forks_count,
            "comments_count": comments_count,
            "my_rating": my_rating,
            "bookmarked": bookmarked,
        }
    )
    return payload


def purge_step(db: Session, step: Step, remove: bool = False):
    purge_attachments(db, "step", step.id)
    db.query(StepProgress).filter(StepProgress.step_id == step.id).delete()
    db.query(Comment).filter(Comment.step_id == step.id).delete()
    db.query(Event).filter(Event.step_id == step.id).update(
        {Event.step_id: None}, synchronize_session=False
    )
    db.query(Reaction).filter(
        Reaction.target_type == "step", Reaction.target_id == step.id
    ).delete()
    if remove:
        db.delete(step)


def sync_steps(db: Session, instruction: Instruction, incoming):
    existing = {step.id: step for step in list(instruction.steps)}
    kept = set()
    for position, data in enumerate(incoming):
        step = existing.get(data.id) if data.id else None
        if step is None:
            step = Step(instruction_id=instruction.id)
            is_new = True
        else:
            kept.add(step.id)
            purge_attachments(db, "step", step.id)
            is_new = False
        step.position = position
        step.title = data.title.strip()
        step.body = data.body or ""
        step.image_url = data.image_url or ""
        if is_new:
            db.add(step)
            db.flush()
        attach_images(db, "step", step.id, getattr(data, "images", []) or [])

    for step in list(instruction.steps):
        if step.id and step.id not in kept:
            purge_step(db, step, remove=True)


def set_tags(db: Session, instruction: Instruction, names: list[str]):
    tags = []
    seen = set()
    for raw in names:
        name = raw.strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        tag = db.query(Tag).filter(Tag.name == name).first()
        if not tag:
            tag = Tag(name=name)
            db.add(tag)
            db.flush()
        tags.append(tag)
    instruction.tags = tags


def delete_instruction(db: Session, instruction: Instruction):
    for step in list(instruction.steps):
        purge_step(db, step)

    for comment in db.query(Comment).filter(Comment.instruction_id == instruction.id).all():
        purge_attachments(db, "comment", comment.id)
    db.query(Comment).filter(Comment.instruction_id == instruction.id).delete()
    db.query(Event).filter(Event.instruction_id == instruction.id).delete()
    db.query(StepProgress).filter(StepProgress.instruction_id == instruction.id).delete()
    db.query(Rating).filter(Rating.instruction_id == instruction.id).delete()
    db.query(Reaction).filter(
        Reaction.target_type == "instruction", Reaction.target_id == instruction.id
    ).delete()
    db.query(Bookmark).filter(Bookmark.instruction_id == instruction.id).delete()
    db.query(Instruction).filter(Instruction.forked_from_id == instruction.id).update(
        {Instruction.forked_from_id: None}, synchronize_session=False
    )
    db.delete(instruction)


def notify(db: Session, user_id: int, kind: str, payload: dict):
    db.add(
        Notification(
            user_id=user_id,
            type=kind,
            payload_json=json.dumps(payload, ensure_ascii=False),
        )
    )


def create_version(db: Session, instruction: Instruction, author_id: int, message: str):
    last = (
        db.query(func.max(InstructionVersion.number))
        .filter(InstructionVersion.instruction_id == instruction.id)
        .scalar()
        or 0
    )
    steps = [
        {
            "id": step.id,
            "position": step.position,
            "title": step.title,
            "body": step.body,
            "image_url": step.image_url,
        }
        for step in sorted(instruction.steps, key=lambda step: step.position)
    ]
    version = InstructionVersion(
        instruction_id=instruction.id,
        number=last + 1,
        steps_json=json.dumps(steps, ensure_ascii=False),
        message=message.strip(),
        author_id=author_id,
    )
    db.add(version)
    db.flush()
    return version


def apply_suggestion(db: Session, comment: Comment, user):
    step = db.get(Step, comment.step_id) if comment.step_id else None
    if not step or step.instruction_id != comment.instruction_id:
        raise ValueError("Шаг не найден")
    instruction = db.get(Instruction, comment.instruction_id)
    step.body = (comment.suggested_body or comment.body).strip()
    comment.accepted_at = datetime.utcnow()
    comment.accepted_by = user.id
    comment.resolved = True
    version = create_version(
        db,
        instruction,
        user.id,
        f"Принято предложение: {comment.user.name}",
    )
    notify(
        db,
        comment.user_id,
        "suggestion_accepted",
        {
            "instruction_id": instruction.id,
            "instruction_title": instruction.title,
            "step_id": step.id,
            "step_title": step.title,
            "comment_id": comment.id,
        },
    )
    return step, version


def attachments_for(db: Session, target_type: str, target_id: int):
    rows = (
        db.query(Attachment)
        .filter(Attachment.target_type == target_type, Attachment.target_id == target_id)
        .order_by(Attachment.position.asc(), Attachment.id.asc())
        .all()
    )
    return [{"id": row.id, "url": row.url, "position": row.position} for row in rows]


def attach_images(db: Session, target_type: str, target_id: int, urls: list[str]):
    for index, url in enumerate(urls):
        if not url:
            continue
        db.add(
            Attachment(
                target_type=target_type,
                target_id=target_id,
                url=url.strip(),
                position=index,
            )
        )


def purge_attachments(db: Session, target_type: str, target_id: int):
    db.query(Attachment).filter(
        Attachment.target_type == target_type,
        Attachment.target_id == target_id,
    ).delete()
