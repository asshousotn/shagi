import re

from rank_bm25 import BM25Okapi
from rapidfuzz import fuzz, process
from sqlalchemy.orm import Session, selectinload

from .models import Instruction

TOKEN_RE = re.compile(r"[a-zа-яё0-9]+", re.I)

SYNONYMS = {
    "пк": ["компьютер", "сборка"],
    "комп": ["компьютер"],
    "компьютер": ["пк"],
    "деканат": ["справка"],
    "докер": ["docker"],
    "доккер": ["docker", "докер"],
    "docker": ["докер"],
    "вайфай": ["wi-fi", "wifi"],
    "wifi": ["wi-fi", "вайфай"],
    "гит": ["git"],
    "git": ["гит"],
    "лаба": ["лабораторная", "отчёт"],
    "общага": ["общежитие"],
    "налог": ["вычет", "ндфл"],
}

state = {"index": None, "ids": [], "titles": []}


def tokens(text: str) -> list[str]:
    return TOKEN_RE.findall((text or "").lower())


def rebuild(db: Session):
    items = (
        db.query(Instruction)
        .options(selectinload(Instruction.steps), selectinload(Instruction.tags))
        .filter(Instruction.status == "published")
        .all()
    )
    docs = []
    ids = []
    titles = []
    for item in items:
        tags = " ".join(tag.name for tag in item.tags)
        steps = " ".join(f"{step.title} {step.body}" for step in item.steps)
        text = " ".join(
            [item.title] * 3
            + [item.summary or ""] * 2
            + [tags] * 2
            + [steps]
        )
        docs.append(tokens(text))
        ids.append(item.id)
        titles.append(item.title)
    state["index"] = BM25Okapi(docs) if docs else None
    state["ids"] = ids
    state["titles"] = titles


def expand(query_tokens: list[str]) -> list[str]:
    result = list(query_tokens)
    for token in query_tokens:
        for synonym in SYNONYMS.get(token, []):
            result.extend(tokens(synonym))
    return result


def search(db: Session, query: str, limit: int = 50) -> list[int]:
    query_tokens = tokens(query)
    index = state["index"]
    if not query_tokens or not index:
        return []

    scores = index.get_scores(query_tokens)
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    ids = [state["ids"][i] for i in ranked if scores[i] > 0][:limit]
    if ids:
        return ids

    expanded = expand(query_tokens)
    scores = index.get_scores(expanded)
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    ids = [state["ids"][i] for i in ranked if scores[i] > 0][:limit]
    if ids:
        return ids

    matches = process.extract(query, state["titles"], scorer=fuzz.WRatio, limit=limit)
    return [state["ids"][idx] for _, score, idx in matches if score >= 50]


def suggest(db: Session, query: str, limit: int = 8) -> list[str]:
    q = (query or "").strip().lower()
    if not q:
        return []
    return [title for title in state["titles"] if q in title.lower()][:limit]
