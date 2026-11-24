import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{BASE_DIR.as_posix()}/app.db"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
AI_FALLBACK_MODELS = os.getenv("AI_FALLBACK_MODELS", "")
OWNER_EMAIL = os.getenv("OWNER_EMAIL", "qqqiy7829@gmail.com")
OWNER_PASSWORD = os.getenv("OWNER_PASSWORD", "")
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
