from app.db import SessionLocal
from app.models import (
    Bookmark,
    Comment,
    Event,
    ForumPost,
    ForumTopic,
    Instruction,
    InstructionVersion,
    Notification,
    Rating,
    Reaction,
    Report,
    Step,
    User,
)

db = SessionLocal()
for name, model in [
    ("users", User),
    ("instructions", Instruction),
    ("steps", Step),
    ("events", Event),
    ("comments", Comment),
    ("ratings", Rating),
    ("reactions", Reaction),
    ("bookmarks", Bookmark),
    ("versions", InstructionVersion),
    ("notifications", Notification),
    ("forum_topics", ForumTopic),
    ("forum_posts", ForumPost),
    ("reports", Report),
]:
    print(name, db.query(model).count())
db.close()
