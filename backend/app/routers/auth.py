from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import create_token, get_current_user, hash_password, verify_password
from ..db import get_db
from ..models import User
from ..schemas import LoginIn, ProfileIn, RegisterIn, TokenOut, UserMe

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    if "@" not in email or "." not in email:
        raise HTTPException(400, "Плохой email")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(400, "Email уже занят")
    user = User(
        email=email,
        password_hash=hash_password(data.password),
        name=data.name.strip(),
        role="student",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"access_token": create_token(user.id), "user": user}


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(400, "Неверный email или пароль")
    return {"access_token": create_token(user.id), "user": user}


@router.get("/me", response_model=UserMe)
def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserMe)
def update_me(
    data: ProfileIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if data.name is not None and data.name.strip():
        user.name = data.name.strip()
    if data.bio is not None:
        user.bio = data.bio.strip()
    if data.avatar_url is not None:
        user.avatar_url = data.avatar_url.strip()
    db.commit()
    db.refresh(user)
    return user
