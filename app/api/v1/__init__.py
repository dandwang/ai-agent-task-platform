from fastapi import APIRouter

from app.api.v1.agent_api import router as agent_router
from app.api.v1.auth_api import router as auth_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["认证"])
api_router.include_router(agent_router, prefix="/agent", tags=["Agent 任务"])
