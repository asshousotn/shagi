from fastapi import Depends, HTTPException

from .auth import get_current_user
from .models import User


def is_admin(user: User | None) -> bool:
    return bool(user and user.role in {"admin", "owner"})


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not is_admin(user):
        raise HTTPException(403, "Нужны права администратора")
    return user


def require_owner(user: User = Depends(get_current_user)) -> User:
    if user.role != "owner":
        raise HTTPException(403, "Только владелец")
    return user
