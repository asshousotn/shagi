from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import SECRET_KEY
from .db import get_db
from .models import User

security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(days=30),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(401, "Нужен вход")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        user = db.get(User, int(payload["sub"]))
    except Exception:
        raise HTTPException(401, "Плохой токен")
    if not user:
        raise HTTPException(401, "Пользователь не найден")
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User | None:
    if not credentials:
        return None
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return db.get(User, int(payload["sub"]))
    except Exception:
        return None


def get_session_id(request: Request) -> str:
    sid = request.headers.get("X-Session-Id") or request.query_params.get("sid")
    if not sid:
        sid = request.client.host if request.client else "anon"
    return sid[:100]


def get_voter_key(request: Request, user: User | None = Depends(get_optional_user)) -> str:
    if user:
        return f"u:{user.id}"
    return f"s:{get_session_id(request)}"
