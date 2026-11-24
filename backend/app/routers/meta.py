from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..helpers import ZERO_STATS, instruction_list_item, ratings_map, reaction_map
from ..models import Category, Instruction, Tag, User
from ..schemas import CategoryOut, TagOut
from ..search import suggest

router = APIRouter(tags=["meta"])


@router.get("/health")
def health():
    return {"ok": True, "app": "shagi"}


@router.get("/categories", response_model=list[CategoryOut])
def categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.name).all()


@router.get("/tags", response_model=list[TagOut])
def tags(db: Session = Depends(get_db)):
    return db.query(Tag).order_by(Tag.name).all()


@router.get("/search/suggest")
def search_suggest(q: str = "", db: Session = Depends(get_db)):
    return {"items": suggest(db, q)}


@router.get("/leaderboard")
def leaderboard(db: Session = Depends(get_db)):
    items = (
        db.query(Instruction)
        .options(
            selectinload(Instruction.steps),
            selectinload(Instruction.author),
            selectinload(Instruction.category),
            selectinload(Instruction.tags),
        )
        .filter(Instruction.status == "published")
        .all()
    )
    ids = [item.id for item in items]
    ratings = ratings_map(db, ids)
    reactions = reaction_map(db, "instruction", ids)
    payload = [instruction_list_item(db, item, ratings, reactions, ZERO_STATS) for item in items]
    payload.sort(key=lambda item: (item["score"], item["views"]), reverse=True)
    top_instructions = payload[:10]

    users = db.query(User).all()
    authors = []
    for user in users:
        own = [item for item in payload if item["author"]["id"] == user.id]
        if not own:
            continue
        authors.append(
            {
                "id": user.id,
                "name": user.name,
                "role": user.role,
                "instructions": len(own),
                "views": sum(item["views"] for item in own),
                "rating_avg": round(
                    sum(item["rating_avg"] for item in own) / len(own), 1
                ),
            }
        )
    authors.sort(key=lambda item: (item["views"], item["instructions"]), reverse=True)
    return {"instructions": top_instructions, "authors": authors[:10]}
