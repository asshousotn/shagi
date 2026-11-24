import secrets

from sqlalchemy import inspect, text

from .auth import hash_password
from .config import OWNER_EMAIL, OWNER_PASSWORD
from .db import Base, SessionLocal, engine
from .models import ForumCategory, User

FORUM_CATEGORIES = [
    ("general", "Общие вопросы", "Всё, что не подошло к другим разделам"),
    ("study", "Учёба", "Вопросы по заданиям и учёбе"),
    ("tech", "Техника и софт", "Железо, программы, настройка"),
    ("docs", "Документы", "Справки, заявления, оформление"),
    ("feedback", "Предложения и баги", "Что улучшить в Taskills"),
]


def add_column(inspector, table, name, definition):
    columns = [column["name"] for column in inspector.get_columns(table)]
    if name not in columns:
        return f"ALTER TABLE {table} ADD COLUMN {name} {definition}"
    return None


def run():
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    forum_tables = set(inspect(engine).get_table_names())
    statements = [
        add_column(inspector, "users", "avatar_url", "TEXT DEFAULT ''"),
        add_column(inspector, "comments", "suggested_body", "TEXT DEFAULT ''"),
        add_column(inspector, "comments", "accepted_at", "DATETIME"),
        add_column(inspector, "comments", "accepted_by", "INTEGER"),
    ]
    if "forum_topics" in forum_tables:
        statements.append(add_column(inspector, "forum_topics", "solved_at", "DATETIME"))
    if "forum_posts" in forum_tables:
        statements.append(add_column(inspector, "forum_posts", "parent_id", "INTEGER"))
        statements.append(add_column(inspector, "forum_posts", "is_solution", "BOOLEAN DEFAULT 0"))
        statements.append(add_column(inspector, "forum_posts", "updated_at", "DATETIME"))
    statements = [statement for statement in statements if statement]
    if statements:
        with engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))
            if "forum_posts" in forum_tables:
                connection.execute(text("UPDATE forum_posts SET updated_at = created_at WHERE updated_at IS NULL"))

    db = SessionLocal()
    try:
        owner = db.query(User).filter(User.email == OWNER_EMAIL).first()
        if not owner:
            password = OWNER_PASSWORD or secrets.token_urlsafe(12)
            owner = User(
                email=OWNER_EMAIL,
                password_hash=hash_password(password),
                name="Owner",
                role="owner",
                bio="Главный администратор Taskills",
            )
            db.add(owner)
            print(f"OWNER created: {OWNER_EMAIL} password: {password}")
        else:
            if owner.role != "owner":
                owner.role = "owner"
                print("OWNER role restored")
            if OWNER_PASSWORD:
                owner.password_hash = hash_password(OWNER_PASSWORD)
                print("OWNER password updated")

        for slug, title, description in FORUM_CATEGORIES:
            category = db.query(ForumCategory).filter(ForumCategory.slug == slug).first()
            if not category:
                db.add(ForumCategory(slug=slug, title=title, description=description))
        db.commit()
    finally:
        db.close()
