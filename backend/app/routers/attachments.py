from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
from ..models import Attachment, Comment, ForumPost, ForumTopic, Instruction, Step
from ..permissions import is_admin
from ..schemas import AttachmentIn, AttachmentOut

router = APIRouter(prefix="/attachments", tags=["attachments"])

TARGETS = {
    "instruction": Instruction,
    "step": Step,
    "topic": ForumTopic,
    "post": ForumPost,
    "comment": Comment,
}


def owner_id_for(db: Session, target_type: str, target_id: int):
    model = TARGETS.get(target_type)
    if not model:
        raise HTTPException(400, "Неизвестный тип вложения")
    target = db.get(model, target_id)
    if not target:
        raise HTTPException(404, "Объект не найден")
    if target_type == "step":
        instruction = db.get(Instruction, target.instruction_id)
        return instruction.author_id if instruction else None
    if target_type == "comment":
        return target.user_id
    return target.author_id


def check_rights(db: Session, target_type: str, target_id: int, user):
    owner_id = owner_id_for(db, target_type, target_id)
    if not is_admin(user) and owner_id != user.id:
        raise HTTPException(403, "Нельзя менять чужие вложения")


@router.post("", response_model=AttachmentOut)
def create_attachment(
    data: AttachmentIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    check_rights(db, data.target_type, data.target_id, user)
    row = Attachment(
        target_type=data.target_type,
        target_id=data.target_id,
        url=data.url.strip(),
        position=data.position,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{attachment_id}")
def delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    row = db.get(Attachment, attachment_id)
    if not row:
        raise HTTPException(404, "Вложение не найдено")
    check_rights(db, row.target_type, row.target_id, user)
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.patch("/{attachment_id}/position", response_model=AttachmentOut)
def move_attachment(
    attachment_id: int,
    position: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    row = db.get(Attachment, attachment_id)
    if not row:
        raise HTTPException(404, "Вложение не найдено")
    check_rights(db, row.target_type, row.target_id, user)
    row.position = position
    db.commit()
    db.refresh(row)
    return row
