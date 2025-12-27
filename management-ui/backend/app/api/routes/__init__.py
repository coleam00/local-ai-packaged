from fastapi import APIRouter
from .auth import router as auth_router
from .services import router as services_router
from .config import router as config_router
from .logs import router as logs_router
from .setup import router as setup_router
from .metrics import router as metrics_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(services_router, prefix="/services", tags=["services"])
api_router.include_router(config_router, prefix="/config", tags=["config"])
api_router.include_router(logs_router, prefix="/logs", tags=["logs"])
api_router.include_router(setup_router, prefix="/setup", tags=["setup"])
api_router.include_router(metrics_router, prefix="/metrics", tags=["metrics"])
