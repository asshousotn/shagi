from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from ..auth import get_current_user, get_voter_key
from ..db import get_db
from ..helpers import (
    ZERO_STATS,
    apply_suggestion,
    attachments_for,
    instruction_list_item,
    purge_attachments,
    rating_info,
    ratings_map,
    reaction_map,
)
from ..models import Bookmark, Comment, ForumPost, ForumTopic, Instruction, Rating, Reaction, Step
from ..schemas import CommentIn, CommentOut, RatingIn, ReactionIn

router = APIRouter(tags=["social"])


def comment_out(db: Session, comment: Comment):
    return {
        "id": comment.id,
        "body": comment.body,
        "kind": comment.kind,
        "resolved": comment.resolved,
        "created_at": comment.created_at,
        "user": {
            "id": comment.user.id,
            "name": comment.user.name,
            "role": comment.user.role,
        },
        "step_id": comment.step_id,
        "parent_id": comment.parent_id,
        "suggested_body": comment.suggested_body or "",
        "accepted_at": comment.accepted_at,
        "accepted_by": comment.accepted_by,
        "images": attachments_for(db, "comment", comment.id),
    }


ARGS = (
    selectinload(Instruction.steps),
    selectinload(Instruction.author),
    selectinload(Instruction.category),
    selectinload(Instruction.tags),
)


@router.get("/instructions/{instruction_id}/comments", response_model=list[CommentOut])
def list_comments(
    instruction_id: int,
    step_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = (
        db.query(Comment)
        .options(selectinload(Comment.user))
        .filter(Comment.instruction_id == instruction_id)
    )
    if step_id:
        query = query.filter(Comment.step_id == step_id)
    comments = query.order_by(Comment.created_at.asc()).all()
    return [comment_out(db, comment) for comment in comments]


@router.post("/instructions/{instruction_id}/comments", response_model=CommentOut)
def add_comment(
    instruction_id: int,
    data: CommentIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    instruction = db.get(Instruction, instruction_id)
    if not instruction:
        raise HTTPException(404, "Инструкция не найдена")
    if data.kind not in {"comment", "suggestion"}:
        raise HTTPException(400, "Плохой тип комментария")
    if data.step_id:
        step = db.get(Step, data.step_id)
        if not step or step.instruction_id != instruction.id:
            raise HTTPException(400, "Шаг не из этой инструкции")
    if data.parent_id:
        parent = db.get(Comment, data.parent_id)
        if not parent or parent.instruction_id != instruction.id:
            raise HTTPException(400, "Родительский комментарий не найден")
    comment = Comment(
        instruction_id=instruction.id,
        step_id=data.step_id,
        user_id=user.id,
        parent_id=data.parent_id,
        kind=data.kind,
        body=data.body.strip(),
        suggested_body=(data.suggested_body or "").strip(),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment_out(db, comment)


@router.post("/comments/{comment_id}/resolve", response_model=CommentOut)
def resolve_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(404, "Комментарий не найден")
    if comment.instruction.author_id != user.id:
        raise HTTPException(403, "Только автор инструкции")
    comment.resolved = not comment.resolved
    db.commit()
    db.refresh(comment)
    return comment_out(db, comment)


@router.post("/comments/{comment_id}/accept", response_model=CommentOut)
def accept_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(404, "Комментарий не найден")
    instruction = db.get(Instruction, comment.instruction_id)
    if not instruction or instruction.author_id != user.id:
        raise HTTPException(403, "Только автор инструкции")
    if not (comment.suggested_body or "").strip():
        raise HTTPException(400, "У предложения нет текста правки")
    try:
        apply_suggestion(db, comment, user)
    except ValueError as error:
        raise HTTPException(404, str(error))
    db.commit()
    db.refresh(comment)
    return comment_out(db, comment)


@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(404, "Комментарий не найден")
    if comment.user_id != user.id and comment.instruction.author_id != user.id:
        raise HTTPException(403, "Нельзя удалить")
    purge_attachments(db, "comment", comment.id)
    db.delete(comment)
    db.commit()
    return {"ok": True}


@router.post("/instructions/{instruction_id}/rating")
def rate_instruction(
    instruction_id: int,
    data: RatingIn,
    db: Session = Depends(get_db),
    voter: str = Depends(get_voter_key),
):
    instruction = db.get(Instruction, instruction_id)
    if not instruction or instruction.status != "published":
        raise HTTPException(404, "Инструкция не найдена")
    rating = (
        db.query(Rating)
        .filter(Rating.instruction_id == instruction.id, Rating.voter_key == voter)
        .first()
    )
    if rating:
        rating.score = data.score
    else:
        db.add(
            Rating(
                instruction_id=instruction.id,
                voter_key=voter,
                score=data.score,
            )
        )
    db.commit()
    avg, count, score = rating_info(db, instruction.id)
    return {
        "rating_avg": avg,
        "rating_count": count,
        "score": score,
        "my_rating": data.score,
    }


@router.post("/reactions")
def react(
    data: ReactionIn,
    db: Session = Depends(get_db),
    voter: str = Depends(get_voter_key),
):
    targets = {
        "instruction": Instruction,
        "step": Step,
        "topic": ForumTopic,
        "post": ForumPost,
    }
    if data.target_type not in targets:
        raise HTTPException(400, "Плохая цель")
    if data.value not in {1, -1}:
        raise HTTPException(400, "Плохая реакция")
    target = db.get(targets[data.target_type], data.target_id)
    if not target:
        raise HTTPException(404, "Цель не найдена")

    existing = (
        db.query(Reaction)
        .filter(
            Reaction.voter_key == voter,
            Reaction.target_type == data.target_type,
            Reaction.target_id == data.target_id,
        )
        .first()
    )
    my_value = 0
    if existing and existing.value == data.value:
        db.delete(existing)
    elif existing:
        existing.value = data.value
        my_value = data.value
    else:
        db.add(
            Reaction(
                voter_key=voter,
                target_type=data.target_type,
                target_id=data.target_id,
                value=data.value,
            )
        )
        my_value = data.value
    db.commit()
    counts = reaction_map(db, data.target_type, [data.target_id])[data.target_id]
    return {"likes": counts["likes"], "dislikes": counts["dislikes"], "my": my_value}


@router.post("/instructions/{instruction_id}/bookmark")
def toggle_bookmark(
    instruction_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    instruction = db.get(Instruction, instruction_id)
    if not instruction:
        raise HTTPException(404, "Инструкция не найдена")
    bookmark = (
        db.query(Bookmark)
        .filter(
            Bookmark.user_id == user.id,
            Bookmark.instruction_id == instruction_id,
        )
        .first()
    )
    if bookmark:
        db.delete(bookmark)
        db.commit()
        return {"bookmarked": False}
    db.add(Bookmark(user_id=user.id, instruction_id=instruction_id))
    db.commit()
    return {"bookmarked": True}


@router.get("/me/bookmarks")
def my_bookmarks(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    items = (
        db.query(Instruction)
        .options(*ARGS)
        .join(Bookmark, Bookmark.instruction_id == Instruction.id)
        .filter(Bookmark.user_id == user.id, Instruction.status == "published")
        .order_by(Bookmark.created_at.desc())
        .all()
    )
    ids = [item.id for item in items]
    ratings = ratings_map(db, ids)
    reactions = reaction_map(db, "instruction", ids)
    return {
        "items": [instruction_list_item(db, item, ratings, reactions, ZERO_STATS) for item in items]
    }


@router.get("/me/inbox")
def inbox(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    comments = (
        db.query(Comment)
        .options(
            selectinload(Comment.user),
            selectinload(Comment.instruction),
            selectinload(Comment.step),
        )
        .join(Instruction, Comment.instruction_id == Instruction.id)
        .filter(
            Instruction.author_id == user.id,
            Comment.kind == "suggestion",
            Comment.resolved.is_(False),
        )
        .order_by(Comment.created_at.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": comment.id,
                "body": comment.body,
                "created_at": comment.created_at,
                "user": comment.user.name,
                "instruction_id": comment.instruction_id,
                "instruction_title": comment.instruction.title,
                "step_id": comment.step_id,
                "step_title": comment.step.title if comment.step else None,
            }
            for comment in comments
        ]
    }
