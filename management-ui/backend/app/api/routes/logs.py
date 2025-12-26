from fastapi import APIRouter, Depends, Query, WebSocket
from typing import List
from ...core.docker_client import DockerClient
from ...core.security import get_current_user
from ..deps import get_docker_client
from ..websocket import verify_ws_token, stream_service_logs, stream_all_status

router = APIRouter()


@router.get("/{service_name}")
async def get_logs(
    service_name: str,
    tail: int = Query(default=100, ge=1, le=10000),
    docker_client: DockerClient = Depends(get_docker_client),
    _: dict = Depends(get_current_user)
):
    """Get recent logs for a service (non-streaming)."""
    container = docker_client.get_container(service_name)
    if not container:
        return {"logs": [], "error": f"Service {service_name} not found"}

    try:
        container_obj = docker_client.client.containers.get(container["full_id"])
        logs = container_obj.logs(tail=tail, timestamps=True).decode("utf-8", errors="replace")
        lines = logs.strip().split("\n") if logs.strip() else []
        return {"logs": lines, "service": service_name, "count": len(lines)}
    except Exception as e:
        return {"logs": [], "error": str(e)}


@router.get("")
async def list_available_logs(
    docker_client: DockerClient = Depends(get_docker_client),
    _: dict = Depends(get_current_user)
):
    """List services that have logs available."""
    containers = docker_client.list_containers()
    available = [
        {
            "service": c["service"],
            "status": c["status"],
            "container_id": c["id"]
        }
        for c in containers
        if c.get("service") and c.get("status") == "running"
    ]
    return {"services": available}


@router.websocket("/ws/{service_name}")
async def websocket_logs(
    websocket: WebSocket,
    service_name: str,
    token: str = Query(...),
    tail: int = Query(default=100)
):
    """WebSocket endpoint for streaming logs."""
    if not verify_ws_token(token):
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    await stream_service_logs(websocket, service_name, tail)


@router.websocket("/ws/status")
async def websocket_status(
    websocket: WebSocket,
    token: str = Query(...)
):
    """WebSocket endpoint for service status updates."""
    if not verify_ws_token(token):
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    await stream_all_status(websocket)
