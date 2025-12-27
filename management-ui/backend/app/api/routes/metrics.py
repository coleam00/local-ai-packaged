from fastapi import APIRouter, Depends, Query, WebSocket, HTTPException, status
from typing import Optional, List
from sqlalchemy.orm import Session
import asyncio

from ...schemas.metrics import (
    ContainerMetrics, AllMetricsResponse, MetricsHistoryResponse,
    HealthAlert, DiagnosticsResponse
)
from ...services.metrics_service import MetricsService
from ...core.docker_client import DockerClient
from ...core.metrics_collector import MetricsCollector
from ...core.security import get_current_user
from ..deps import get_docker_client, get_db
from ..websocket import verify_ws_token
from ...config import settings
from datetime import datetime


router = APIRouter()


def get_metrics_service(
    docker_client: DockerClient = Depends(get_docker_client),
    db: Session = Depends(get_db)
) -> MetricsService:
    return MetricsService(docker_client, db)


@router.get("", response_model=AllMetricsResponse)
async def get_all_metrics(
    metrics_service: MetricsService = Depends(get_metrics_service),
    _: dict = Depends(get_current_user)
):
    """Get current metrics for all services."""
    metrics = metrics_service.get_all_current_metrics()
    return AllMetricsResponse(metrics=metrics, timestamp=datetime.utcnow())


@router.get("/alerts/active", response_model=List[HealthAlert])
async def get_active_alerts(
    service_name: Optional[str] = None,
    metrics_service: MetricsService = Depends(get_metrics_service),
    _: dict = Depends(get_current_user)
):
    """Get active (unacknowledged) alerts."""
    return metrics_service.get_active_alerts(service_name)


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    metrics_service: MetricsService = Depends(get_metrics_service),
    _: dict = Depends(get_current_user)
):
    """Acknowledge an alert."""
    if not metrics_service.acknowledge_alert(alert_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' not found"
        )
    return {"success": True}


@router.get("/{service_name}", response_model=ContainerMetrics)
async def get_service_metrics(
    service_name: str,
    metrics_service: MetricsService = Depends(get_metrics_service),
    _: dict = Depends(get_current_user)
):
    """Get current metrics for a specific service."""
    metrics = metrics_service.get_current_metrics(service_name)
    if not metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service '{service_name}' not found or not running"
        )
    return metrics


@router.get("/{service_name}/history", response_model=MetricsHistoryResponse)
async def get_metrics_history(
    service_name: str,
    hours: int = Query(default=24, ge=1, le=168),
    metrics_service: MetricsService = Depends(get_metrics_service),
    _: dict = Depends(get_current_user)
):
    """Get metrics history for a service (up to 7 days)."""
    return metrics_service.get_metrics_history(service_name, hours)


@router.get("/{service_name}/diagnostics", response_model=DiagnosticsResponse)
async def get_diagnostics(
    service_name: str,
    metrics_service: MetricsService = Depends(get_metrics_service),
    _: dict = Depends(get_current_user)
):
    """Run diagnostics for a service."""
    return metrics_service.get_diagnostics(service_name)


@router.websocket("/ws")
async def websocket_metrics(
    websocket: WebSocket,
    token: str = Query(...),
    interval: float = Query(default=2.0, ge=1.0, le=10.0)
):
    """WebSocket endpoint for streaming metrics for all services."""
    if not verify_ws_token(token):
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()

    docker_client = DockerClient(
        project=settings.COMPOSE_PROJECT_NAME,
        base_path=settings.COMPOSE_BASE_PATH
    )
    collector = MetricsCollector(docker_client.client)

    try:
        while True:
            metrics = collector.get_all_container_stats(docker_client.project)
            await websocket.send_json({
                "type": "metrics",
                "timestamp": datetime.utcnow().isoformat(),
                "data": metrics
            })
            await asyncio.sleep(interval)
    except Exception:
        pass


@router.websocket("/ws/{service_name}")
async def websocket_service_metrics(
    websocket: WebSocket,
    service_name: str,
    token: str = Query(...),
    interval: float = Query(default=2.0, ge=1.0, le=10.0)
):
    """WebSocket endpoint for streaming metrics for a specific service."""
    if not verify_ws_token(token):
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()

    docker_client = DockerClient(
        project=settings.COMPOSE_PROJECT_NAME,
        base_path=settings.COMPOSE_BASE_PATH
    )
    collector = MetricsCollector(docker_client.client)

    container = docker_client.get_container(service_name)
    if not container:
        await websocket.send_json({
            "type": "error",
            "message": f"Service {service_name} not found"
        })
        await websocket.close()
        return

    try:
        prev_stats = None
        prev_time = None

        while True:
            try:
                container_obj = docker_client.client.containers.get(container["full_id"])
                stats = container_obj.stats(stream=False)
                current_time = datetime.utcnow()

                parsed = collector._parse_stats_with_delta(
                    service_name,
                    container["id"],
                    stats,
                    prev_stats,
                    prev_time,
                    current_time
                )

                if parsed:
                    await websocket.send_json({
                        "type": "metrics",
                        "data": parsed
                    })

                prev_stats = stats
                prev_time = current_time
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
                break

            await asyncio.sleep(interval)
    except Exception:
        pass
