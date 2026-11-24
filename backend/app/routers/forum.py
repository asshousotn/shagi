from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from ..auth import get_current_user
from ..db import get_db
from ..helpers import attach_images, attachments_for, notify, purge_attachments
from ..models import ForumCategory, ForumPost, ForumTopic, Instruction, User
from ..permissions import is_admin
from ..schemas import (
    ForumCategoryOut,
    ForumPostIn,
    ForumPostUpdate,
    ForumTopicIn,
    ForumTopicOut,
)

router = APIRouter(prefix="/forum", tags=["forum"])


def topic_out(db: Session, topic: ForumTopic, with_posts: bool = False):
    author = db.get(User, topic.author_id)
    posts = (
        db.query(ForumPost)
        .options(selectinload(ForumPost.author))
        .filter(ForumPost.topic_id == topic.id)
        .order_by(ForumPost.created_at.asc())
        .all()
    )
    return {
        "id": topic.id,
        "category_id": topic.category_id,
        "instruction_id": topic.instruction_id,
        "author": {
            "id": author.id,
            "name": author.name,
            "role": author.role,
        },
        "title": topic.title,
        "body": topic.body,
        "pinned": topic.pinned,
        "closed": topic.closed,
        "views": topic.views,
        "solved_at": topic.solved_at,
        "images": attachments_for(db, "topic", topic.id),
        "created_at": topic.created_at,
        "updated_at": topic.updated_at,
        "posts_count": len(posts),
        "posts": [
            {
                "id": post.id,
                "author": {
                    "id": post.author.id,
                    "name": post.author.name,
                    "role": post.author.role,
                },
                "body": post.body,
                "parent_id": post.parent_id,
                "is_solution": post.is_solution,
                "images": attachments_for(db, "post", post.id),
                "created_at": post.created_at,
                "updated_at": post.updated_at,
            }
            for post in posts
        ]
        if with_posts
        else [],
    }


@router.get("/categories", response_model=list[ForumCategoryOut])
def forum_categories(db: Session = Depends(get_db)):
    return db.query(ForumCategory).order_by(ForumCategory.id).all()


@router.get("/topics")
def forum_topics(
    category: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query = db.query(ForumTopic)
    if category:
        query = query.filter(ForumTopic.category_id == category)
    total = query.count()
    topics = (
        query.order_by(ForumTopic.pinned.desc(), ForumTopic.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [topic_out(db, topic) for topic in topics],
        "total": total,
        "page": page,
        "pages": (total + page_size - 1) // page_size if total else 0,
    }


@router.get("/topics/{topic_id}", response_model=ForumTopicOut)
def forum_topic(topic_id: int, db: Session = Depends(get_db)):
    topic = db.get(ForumTopic, topic_id)
    if not topic:
        raise HTTPException(404, "Тема не найдена")
    topic.views += 1
    db.commit()
    db.refresh(topic)
    return topic_out(db, topic, with_posts=True)


@router.post("/topics", response_model=ForumTopicOut)
def create_topic(
    data: ForumTopicIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    category = db.get(ForumCategory, data.category_id)
    if not category:
        raise HTTPException(400, "Раздел не найден")
    if data.instruction_id and not db.get(Instruction, data.instruction_id):
        raise HTTPException(400, "Инструкция не найдена")
    topic = ForumTopic(
        category_id=data.category_id,
        instruction_id=data.instruction_id,
        author_id=user.id,
        title=data.title.strip(),
        body=data.body.strip(),
    )
    db.add(topic)
    db.flush()
    attach_images(db, "topic", topic.id, data.images)
    db.commit()
    db.refresh(topic)
    return topic_out(db, topic, with_posts=True)


@router.post("/topics/{topic_id}/posts", response_model=ForumTopicOut)
def create_post(
    topic_id: int,
    data: ForumPostIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    topic = db.get(ForumTopic, topic_id)
    if not topic:
        raise HTTPException(404, "Тема не найдена")
    if topic.closed:
        raise HTTPException(403, "Тема закрыта")
    parent = None
    if data.parent_id:
        parent = db.get(ForumPost, data.parent_id)
        if not parent or parent.topic_id != topic.id:
            raise HTTPException(400, "Родительский ответ не из этой темы")
    post = ForumPost(
        topic_id=topic.id,
        author_id=user.id,
        body=data.body.strip(),
        parent_id=data.parent_id,
    )
    db.add(post)
    db.flush()
    attach_images(db, "post", post.id, data.images)
    notify(
        db,
        topic.author_id,
        "forum_reply",
        {
            "topic_id": topic.id,
            "topic_title": topic.title,
            "post_id": post.id,
            "user": user.name,
        },
    )
    if parent and parent.author_id != topic.author_id and parent.author_id != user.id:
        notify(
            db,
            parent.author_id,
            "forum_quote",
            {
                "topic_id": topic.id,
                "topic_title": topic.title,
                "post_id": post.id,
                "user": user.name,
            },
        )
    topic.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(topic)
    return topic_out(db, topic, with_posts=True)


@router.patch("/posts/{post_id}", response_model=ForumTopicOut)
def edit_post(
    post_id: int,
    data: ForumPostUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    post = db.get(ForumPost, post_id)
    if not post:
        raise HTTPException(404, "Ответ не найден")
    if post.author_id != user.id and not is_admin(user):
        raise HTTPException(403, "Нельзя редактировать чужой ответ")
    post.body = data.body.strip()
    post.updated_at = datetime.utcnow()
    topic = db.get(ForumTopic, post.topic_id)
    db.commit()
    db.refresh(topic)
    return topic_out(db, topic, with_posts=True)


@router.post("/posts/{post_id}/solution", response_model=ForumTopicOut)
def mark_solution(
    post_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    post = db.get(ForumPost, post_id)
    if not post:
        raise HTTPException(404, "Ответ не найден")
    topic = db.get(ForumTopic, post.topic_id)
    if not is_admin(user) and topic.author_id != user.id:
        raise HTTPException(403, "Только автор темы или админ")
    for other in db.query(ForumPost).filter(ForumPost.topic_id == topic.id).all():
        other.is_solution = False
    post.is_solution = True
    topic.solved_at = datetime.utcnow()
    notify(
        db,
        post.author_id,
        "solution_marked",
        {"topic_id": topic.id, "topic_title": topic.title, "post_id": post.id},
    )
    db.commit()
    db.refresh(topic)
    return topic_out(db, topic, with_posts=True)


@router.post("/topics/{topic_id}/close", response_model=ForumTopicOut)
def close_topic(
    topic_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    topic = db.get(ForumTopic, topic_id)
    if not topic:
        raise HTTPException(404, "Тема не найдена")
    if not is_admin(user) and topic.author_id != user.id:
        raise HTTPException(403, "Нельзя закрыть чужую тему")
    topic.closed = not topic.closed
    db.commit()
    db.refresh(topic)
    return topic_out(db, topic, with_posts=True)


@router.delete("/posts/{post_id}")
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    post = db.get(ForumPost, post_id)
    if not post:
        raise HTTPException(404, "Сообщение не найдено")
    if not is_admin(user) and post.author_id != user.id:
        raise HTTPException(403, "Нельзя удалить чужое сообщение")
    purge_attachments(db, "post", post.id)
    db.delete(post)
    db.commit()
    return {"ok": True}


@router.get("/instructions/{instruction_id}/topics")
def instruction_topics(instruction_id: int, db: Session = Depends(get_db)):
    topics = (
        db.query(ForumTopic)
        .filter(ForumTopic.instruction_id == instruction_id)
        .order_by(ForumTopic.updated_at.desc())
        .limit(20)
        .all()
    )
    return {"items": [topic_out(db, topic) for topic in topics]}
