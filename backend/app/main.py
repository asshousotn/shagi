import mimetypes

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import BASE_DIR, UPLOAD_DIR
from .db import SessionLocal
from .migrations import run as run_migrations
from .routers import (
    admin,
    analytics,
    attachments,
    auth,
    forum,
    instructions,
    meta,
    progress,
    social,
    uploads,
    users,
)
from .routers import ai as ai_router
from .search import rebuild
from .seed import seed

mimetypes.add_type("application/vnd.android.package-archive", ".apk")
mimetypes.add_type("application/x-apple-aspen-config", ".mobileconfig")

app = FastAPI(title="Taskills", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    auth.router,
    users.router,
    instructions.router,
    social.router,
    progress.router,
    analytics.router,
    meta.router,
    forum.router,
    admin.router,
    ai_router.router,
    uploads.router,
    attachments.router,
):
    app.include_router(router, prefix="/api")

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

DIST = BASE_DIR.parent / "frontend" / "dist"
if (DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")


@app.on_event("startup")
def on_startup():
    run_migrations()
    db = SessionLocal()
    try:
        seed(db)
        rebuild(db)
    finally:
        db.close()


if DIST.exists():
    @app.get("/{path:path}")
    def spa(path: str):
        target = DIST / path
        if path and target.is_file():
            return FileResponse(target)
        return FileResponse(DIST / "index.html")
