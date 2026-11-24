from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ..auth import get_current_user
from ..config import UPLOAD_DIR
from ..schemas import UploadOut

router = APIRouter(tags=["uploads"])

ALLOWED = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}


@router.post("/uploads", response_model=UploadOut)
async def upload(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(400, "Нужна картинка")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED:
        suffix = ".png"
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(400, "Файл больше 5 МБ")
    name = f"{uuid4().hex}{suffix}"
    (UPLOAD_DIR / name).write_bytes(data)
    return {"url": f"/uploads/{name}"}
