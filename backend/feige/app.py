from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.feige.api.admin import build_admin_router
from backend.feige.auth import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    authenticate,
    make_session_token,
    new_csrf_token,
    read_session_token,
)
from backend.feige.database import connect, init_database
from backend.feige.integrations.mock_douyin import MockDouyinAdapter
from backend.feige.services.annotations import AnnotationService
from backend.feige.services.analytics import AnalyticsService
from backend.feige.services.assistant import SuggestionService
from backend.feige.services.knowledge import KnowledgeService
from backend.feige.services.read_queries import ReadQueries
from backend.feige.services.sync import SyncService


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = ROOT_DIR / "data" / "feige_assist.db"
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"


class LoginRequest(BaseModel):
    username: str
    password: str


def create_feige_app(
    db_path: Path | None = None,
    session_secret: str = "feige-local-session-secret",
) -> FastAPI:
    resolved_db = Path(db_path) if db_path else DEFAULT_DB_PATH
    init_database(resolved_db)
    adapter = MockDouyinAdapter(resolved_db, "demo-webhook-secret")
    read_queries = ReadQueries(resolved_db)
    annotation_service = AnnotationService(resolved_db)
    knowledge_service = KnowledgeService(resolved_db)
    suggestion_service = SuggestionService(resolved_db, knowledge_service)
    analytics_service = AnalyticsService(resolved_db)
    sync_service = SyncService(
        resolved_db,
        adapter,
        "demo-webhook-secret",
        suggestion_service=suggestion_service,
    )

    app = FastAPI(title="飞鸽只读 AI 辅助中台", version="1.0.0")
    app.state.db_path = resolved_db
    app.state.sync_service = sync_service
    app.state.read_queries = read_queries
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/auth/login")
    def login(payload: LoginRequest, response: Response) -> dict:
        with connect(resolved_db) as connection:
            admin = authenticate(connection, payload.username, payload.password)
        if not admin:
            from fastapi import HTTPException

            raise HTTPException(status_code=401, detail="用户名或密码错误")
        session_token = make_session_token(session_secret, admin["username"])
        csrf_token = new_csrf_token()
        response.set_cookie(
            SESSION_COOKIE,
            session_token,
            httponly=True,
            samesite="lax",
            max_age=12 * 60 * 60,
        )
        response.set_cookie(
            CSRF_COOKIE,
            csrf_token,
            httponly=False,
            samesite="lax",
            max_age=12 * 60 * 60,
        )
        return {
            "authenticated": True,
            "username": admin["username"],
            "csrf_token": csrf_token,
        }

    @app.get("/api/auth/session")
    def session(request: Request) -> dict:
        username = read_session_token(
            session_secret,
            request.cookies.get(SESSION_COOKIE),
        )
        return {
            "authenticated": bool(username),
            "username": username,
            "csrf_token": request.cookies.get(CSRF_COOKIE, ""),
        }

    @app.post("/api/auth/logout")
    def logout(response: Response) -> dict[str, bool]:
        response.delete_cookie(SESSION_COOKIE)
        response.delete_cookie(CSRF_COOKIE)
        return {"ok": True}

    app.include_router(
        build_admin_router(
            read_queries,
            sync_service,
            annotation_service,
            knowledge_service,
            suggestion_service,
            analytics_service,
            session_secret,
        )
    )

    if (FRONTEND_DIST / "assets").exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        index_file = FRONTEND_DIST / "index.html"
        if not index_file.exists():
            return HTMLResponse(
                "<h1>前端尚未构建</h1><p>请运行 npm run build。</p>",
                status_code=503,
            )
        return FileResponse(index_file)

    return app
