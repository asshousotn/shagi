from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user, hash_password
from ..db import get_db
from ..models import (
    Comment,
    ForumPost,
    ForumTopic,
    Instruction,
    Report,
    User,
)
from ..permissions import require_admin, require_owner
from ..schemas import AdminUserOut, PasswordIn, ReportIn, ReportOut, RoleIn

router = APIRouter(prefix="/admin", tags=["admin"])


def report_out(db: Session, report: Report):
    reporter = db.get(User, report.reporter_id)
    return {
        "id": report.id,
        "reporter": reporter.name if reporter else "?",
        "target_type": report.target_type,
        "target_id": report.target_id,
        "reason": report.reason or "",
        "status": report.status,
        "created_at": report.created_at,
    }


@router.get("/stats")
def admin_stats(db: Session = Depends(get_db), admin=Depends(require_admin)):
    return {
        "users": db.query(User).count(),
        "instructions": db.query(Instruction).count(),
        "topics": db.query(ForumTopic).count(),
        "posts": db.query(ForumPost).count(),
        "open_reports": db.query(Report).filter(Report.status == "open").count(),
    }


@router.get("/users", response_model=list[AdminUserOut])
def admin_users(db: Session = Depends(get_db), admin=Depends(require_admin)):
    result = []
    for user in db.query(User).order_by(User.id).all():
        result.append(
            {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "instructions": db.query(Instruction).filter(Instruction.author_id == user.id).count(),
                "created_at": user.created_at,
            }
        )
    return result


@router.post("/users/{user_id}/role", response_model=AdminUserOut)
def set_role(
    user_id: int,
    data: RoleIn,
    db: Session = Depends(get_db),
    owner=Depends(require_owner),
):
    if data.role not in {"student", "expert", "admin"}:
        raise HTTPException(400, "Недопустимая роль")
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "Пользователь не найден")
    if target.role == "owner":
        raise HTTPException(403, "Владельца менять нельзя")
    target.role = data.role
    db.commit()
    db.refresh(target)
    return {
        "id": target.id,
        "email": target.email,
        "name": target.name,
        "role": target.role,
        "instructions": db.query(Instruction).filter(Instruction.author_id == target.id).count(),
        "created_at": target.created_at,
    }


@router.post("/users/{user_id}/password")
def reset_password(
    user_id: int,
    data: PasswordIn,
    db: Session = Depends(get_db),
    owner=Depends(require_owner),
):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "Пользователь не найден")
    if target.role == "owner":
        raise HTTPException(403, "Пароль владельца меняется только через env")
    target.password_hash = hash_password(data.password)
    db.commit()
    return {"ok": True}


@router.post("/reports", response_model=ReportOut)
def create_report(
    data: ReportIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if data.target_type not in {"instruction", "comment", "topic", "post"}:
        raise HTTPException(400, "Неизвестный тип жалобы")
    model = {
        "instruction": Instruction,
        "comment": Comment,
        "topic": ForumTopic,
        "post": ForumPost,
    }[data.target_type]
    if not db.get(model, data.target_id):
        raise HTTPException(404, "Объект не найден")
    report = Report(
        reporter_id=user.id,
        target_type=data.target_type,
        target_id=data.target_id,
        reason=data.reason.strip(),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report_out(db, report)


@router.get("/reports", response_model=list[ReportOut])
def admin_reports(db: Session = Depends(get_db), admin=Depends(require_admin)):
    reports = db.query(Report).order_by(Report.created_at.desc()).limit(100).all()
    return [report_out(db, report) for report in reports]


@router.post("/reports/{report_id}/resolve", response_model=ReportOut)
def resolve_report(
    report_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(404, "Жалоба не найдена")
    report.status = "resolved"
    report.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(report)
    return report_out(db, report)
