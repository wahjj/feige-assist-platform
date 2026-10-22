from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from backend.feige.services.sync import SyncService


def build_integration_router(sync_service: SyncService) -> APIRouter:
    router = APIRouter(prefix="/integrations/doudian")

    @router.post("/feige/events")
    async def feige_events(request: Request):
        raw_body = await request.body()
        headers = {key: value for key, value in request.headers.items()}
        result = await run_in_threadpool(
            sync_service.ingest_webhook,
            raw_body,
            headers,
        )
        status_code = 401 if result.status == "invalid_signature" else 200
        return JSONResponse(result.model_dump(mode="json"), status_code=status_code)

    @router.get("/oauth/start")
    def oauth_start() -> dict:
        return {
            "status": "demo_only",
            "authorization_url": None,
            "message": "本地模拟环境不需要真实抖店授权，真实接入时替换此端点。",
        }

    @router.post("/oauth/callback")
    def oauth_callback() -> dict:
        return {
            "status": "demo_connected",
            "readonly": True,
            "message": "本地模拟授权完成，不会获取任何真实 Token。",
        }

    return router
