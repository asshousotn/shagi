from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .db import Base

instruction_tags = Table(
    "instruction_tags",
    Base.metadata,
    Column("instruction_id", ForeignKey("instructions.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, default="student", nullable=False)
    bio = Column(Text, default="")
    avatar_url = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    instructions = relationship(
        "Instruction",
        back_populates="author",
        foreign_keys="Instruction.author_id",
    )


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    instructions = relationship("Instruction", back_populates="category")


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)


class Instruction(Base):
    __tablename__ = "instructions"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    summary = Column(Text, default="")
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String, default="draft", nullable=False, index=True)
    difficulty = Column(String, default="medium", nullable=False)
    minutes = Column(Integer, default=15)
    cover_url = Column(Text, default="")
    forked_from_id = Column(Integer, ForeignKey("instructions.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    views = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)

    author = relationship("User", back_populates="instructions", foreign_keys=[author_id])
    category = relationship("Category", back_populates="instructions")
    steps = relationship(
        "Step",
        back_populates="instruction",
        cascade="all, delete-orphan",
        order_by="Step.position",
    )
    tags = relationship("Tag", secondary=instruction_tags, backref="instructions")
    forked_from = relationship("Instruction", remote_side=[id], foreign_keys=[forked_from_id])


class Step(Base):
    __tablename__ = "steps"

    id = Column(Integer, primary_key=True)
    instruction_id = Column(
        Integer,
        ForeignKey("instructions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position = Column(Integer, default=0, nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text, default="")
    image_url = Column(Text, default="")

    instruction = relationship("Instruction", back_populates="steps")


class StepProgress(Base):
    __tablename__ = "step_progress"

    id = Column(Integer, primary_key=True)
    session_id = Column(String, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    instruction_id = Column(
        Integer,
        ForeignKey("instructions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_id = Column(Integer, ForeignKey("steps.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, default="viewed", nullable=False)
    time_ms = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("session_id", "step_id", name="uq_progress_session_step"),
    )


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    session_id = Column(String, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    instruction_id = Column(
        Integer,
        ForeignKey("instructions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_id = Column(Integer, ForeignKey("steps.id", ondelete="SET NULL"), nullable=True, index=True)
    type = Column(String, nullable=False, index=True)
    duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_events_instruction_step_type", "instruction_id", "step_id", "type"),
    )


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True)
    instruction_id = Column(
        Integer,
        ForeignKey("instructions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_id = Column(Integer, ForeignKey("steps.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("comments.id", ondelete="CASCADE"), nullable=True)
    kind = Column(String, default="comment", nullable=False)
    body = Column(Text, nullable=False)
    suggested_body = Column(Text, default="")
    resolved = Column(Boolean, default=False, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    accepted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    instruction = relationship("Instruction")
    step = relationship("Step")
    user = relationship("User", foreign_keys=[user_id])
    accepted_by_user = relationship("User", foreign_keys=[accepted_by])


class Reaction(Base):
    __tablename__ = "reactions"

    id = Column(Integer, primary_key=True)
    voter_key = Column(String, nullable=False, index=True)
    target_type = Column(String, nullable=False)
    target_id = Column(Integer, nullable=False)
    value = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("voter_key", "target_type", "target_id", name="uq_reaction_voter_target"),
    )


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True)
    voter_key = Column(String, nullable=False, index=True)
    instruction_id = Column(
        Integer,
        ForeignKey("instructions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("voter_key", "instruction_id", name="uq_rating_voter_instruction"),
    )


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    instruction_id = Column(
        Integer,
        ForeignKey("instructions.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "instruction_id", name="uq_bookmark"),
    )


class InstructionVersion(Base):
    __tablename__ = "instruction_versions"

    id = Column(Integer, primary_key=True)
    instruction_id = Column(
        Integer,
        ForeignKey("instructions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    number = Column(Integer, nullable=False)
    steps_json = Column(Text, nullable=False)
    message = Column(Text, default="")
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    author = relationship("User")

    __table_args__ = (
        UniqueConstraint("instruction_id", "number", name="uq_version_number"),
    )


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String, nullable=False)
    payload_json = Column(Text, default="{}")
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class ForumCategory(Base):
    __tablename__ = "forum_categories"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, default="")


class ForumTopic(Base):
    __tablename__ = "forum_topics"

    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("forum_categories.id"), nullable=False, index=True)
    instruction_id = Column(Integer, ForeignKey("instructions.id", ondelete="SET NULL"), nullable=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    pinned = Column(Boolean, default=False, nullable=False)
    closed = Column(Boolean, default=False, nullable=False)
    views = Column(Integer, default=0, nullable=False)
    solved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ForumPost(Base):
    __tablename__ = "forum_posts"

    id = Column(Integer, primary_key=True)
    topic_id = Column(Integer, ForeignKey("forum_topics.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("forum_posts.id", ondelete="CASCADE"), nullable=True, index=True)
    body = Column(Text, nullable=False)
    is_solution = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    author = relationship("User")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_type = Column(String, nullable=False)
    target_id = Column(Integer, nullable=False)
    reason = Column(Text, default="")
    status = Column(String, default="open", nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True)
    target_type = Column(String, nullable=False, index=True)
    target_id = Column(Integer, nullable=False, index=True)
    url = Column(Text, nullable=False)
    position = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
