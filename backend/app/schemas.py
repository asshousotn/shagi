from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    role: str
    bio: str = ""
    avatar_url: str = ""


class UserMe(UserOut):
    email: str


class RegisterIn(BaseModel):
    email: str
    password: str = Field(min_length=4)
    name: str = Field(min_length=1)


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserMe


class ProfileIn(BaseModel):
    name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None


class StepIn(BaseModel):
    id: int | None = None
    title: str = Field(min_length=1)
    body: str = ""
    image_url: str = ""
    images: list[str] = []


class AttachmentOut(BaseModel):
    id: int
    url: str
    position: int = 0


class AttachmentIn(BaseModel):
    target_type: str
    target_id: int
    url: str = Field(min_length=1)
    position: int = 0


class StepOut(BaseModel):
    id: int
    position: int
    title: str
    body: str
    image_url: str
    images: list[AttachmentOut] = []
    likes: int = 0
    dislikes: int = 0


class InstructionIn(BaseModel):
    title: str = Field(min_length=2)
    summary: str = ""
    category_id: int | None = None
    difficulty: str = "medium"
    minutes: int = Field(default=15, ge=1)
    cover_url: str = ""
    images: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    steps: list[StepIn] = Field(default_factory=list)


class AuthorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    role: str


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class InstructionListItem(BaseModel):
    id: int
    title: str
    summary: str
    author: AuthorOut
    category: CategoryOut | None = None
    difficulty: str
    minutes: int
    cover_url: str
    status: str
    verified_at: datetime | None = None
    forked_from_id: int | None = None
    created_at: datetime
    rating_avg: float = 0
    rating_count: int = 0
    score: float = 0
    steps_count: int = 0
    views: int = 0
    likes: int = 0
    dislikes: int = 0
    completion_rate: float = 0
    starts: int = 0


class InstructionDetail(InstructionListItem):
    steps: list[StepOut]
    images: list[AttachmentOut] = []
    tags: list[TagOut]
    forks_count: int = 0
    comments_count: int = 0
    my_rating: int | None = None
    bookmarked: bool = False


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    body: str
    kind: str
    resolved: bool
    created_at: datetime
    user: AuthorOut
    step_id: int | None = None
    parent_id: int | None = None
    suggested_body: str = ""
    accepted_at: datetime | None = None
    accepted_by: int | None = None
    images: list[AttachmentOut] = []


class CommentIn(BaseModel):
    body: str = Field(min_length=1)
    step_id: int | None = None
    parent_id: int | None = None
    kind: str = "comment"
    suggested_body: str = ""


class RatingIn(BaseModel):
    score: int = Field(ge=1, le=5)


class ReactionIn(BaseModel):
    target_type: str
    target_id: int
    value: int


class EventIn(BaseModel):
    type: str
    instruction_id: int
    step_id: int | None = None
    duration_ms: int = 0


class AIInstructionIn(BaseModel):
    goal: str = Field(min_length=2)
    audience: str = ""
    level: str = ""


class AIImproveIn(BaseModel):
    text: str = Field(min_length=1)


class AITagsIn(BaseModel):
    title: str = Field(min_length=1)
    summary: str = ""


class UploadOut(BaseModel):
    url: str


class VersionOut(BaseModel):
    id: int
    number: int
    message: str
    created_at: datetime
    author: AuthorOut | None = None
    steps: list[StepOut]


class NotificationOut(BaseModel):
    id: int
    type: str
    payload: dict
    read_at: datetime | None = None
    created_at: datetime


class CoachIn(BaseModel):
    step_id: int


class CoachApplyIn(BaseModel):
    step_id: int
    body: str = Field(min_length=1)
    message: str = ""


class ForumCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    description: str = ""


class ForumPostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    author: AuthorOut
    body: str
    parent_id: int | None = None
    is_solution: bool = False
    images: list[AttachmentOut] = []
    created_at: datetime
    updated_at: datetime | None = None


class ForumTopicOut(BaseModel):
    id: int
    category_id: int
    instruction_id: int | None = None
    author: AuthorOut
    title: str
    body: str
    pinned: bool = False
    closed: bool = False
    views: int = 0
    solved_at: datetime | None = None
    images: list[AttachmentOut] = []
    created_at: datetime
    updated_at: datetime
    posts_count: int = 0
    posts: list[ForumPostOut] = []


class ForumTopicIn(BaseModel):
    title: str = Field(min_length=3)
    body: str = Field(min_length=1)
    category_id: int
    instruction_id: int | None = None
    images: list[str] = []


class ForumPostIn(BaseModel):
    body: str = Field(min_length=1)
    parent_id: int | None = None
    images: list[str] = []


class ForumPostUpdate(BaseModel):
    body: str = Field(min_length=1)


class ReportIn(BaseModel):
    target_type: str
    target_id: int
    reason: str = ""


class ReportOut(BaseModel):
    id: int
    reporter: str
    target_type: str
    target_id: int
    reason: str
    status: str
    created_at: datetime


class AdminUserOut(BaseModel):
    id: int
    email: str
    name: str
    role: str
    instructions: int
    created_at: datetime


class RoleIn(BaseModel):
    role: str


class PasswordIn(BaseModel):
    password: str = Field(min_length=4)
