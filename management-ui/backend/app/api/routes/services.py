from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from ...schemas.service import (
    ServiceListResponse, ServiceDetailResponse, ServiceActionRequest,
    ServiceActionResponse, DependencyGraphResponse, ServiceGroupsResponse,
    ServiceGroupInfo
)
from ...services.docker_service import DockerService
from ...core.docker_client import DockerClient
from ...core.compose_parser import ComposeParser
from ...core.dependency_graph import DependencyGraph
from ..deps import (
    get_docker_client, get_compose_parser, get_dependency_graph,
    get_current_db_user
)
from ...core.security import get_current_user

router = APIRouter()

def get_docker_service(
    docker_client: DockerClient = Depends(get_docker_client),
    parser: ComposeParser = Depends(get_compose_parser),
    graph: DependencyGraph = Depends(get_dependency_graph)
) -> DockerService:
    return DockerService(docker_client, parser, graph)

@router.get("", response_model=ServiceListResponse)
async def list_services(
    docker_service: DockerService = Depends(get_docker_service),
    _: dict = Depends(get_current_user)  # Require auth
):
    """List all services with their current status."""
    services = docker_service.list_services()
    return ServiceListResponse(services=services, total=len(services))

@router.get("/groups", response_model=ServiceGroupsResponse)
async def get_service_groups(
    docker_service: DockerService = Depends(get_docker_service),
    _: dict = Depends(get_current_user)
):
    """Get service groups with running counts."""
    groups_data = docker_service.get_groups_with_status()
    groups = [
        ServiceGroupInfo(**data)
        for data in groups_data.values()
    ]
    return ServiceGroupsResponse(groups=sorted(groups, key=lambda g: g.name))

@router.get("/dependencies", response_model=DependencyGraphResponse)
async def get_dependency_graph_data(
    graph: DependencyGraph = Depends(get_dependency_graph),
    _: dict = Depends(get_current_user)
):
    """Get dependency graph for visualization."""
    return graph.to_visualization_format()

@router.get("/{service_name}", response_model=ServiceDetailResponse)
async def get_service_detail(
    service_name: str,
    docker_service: DockerService = Depends(get_docker_service),
    _: dict = Depends(get_current_user)
):
    """Get detailed information about a specific service."""
    service = docker_service.get_service(service_name)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service '{service_name}' not found"
        )
    return service

@router.post("/{service_name}/start", response_model=ServiceActionResponse)
async def start_service(
    service_name: str,
    request: ServiceActionRequest = None,
    docker_service: DockerService = Depends(get_docker_service),
    _: dict = Depends(get_current_user)
):
    """Start a service."""
    request = request or ServiceActionRequest()
    result = docker_service.start_service(
        service_name,
        profile=request.profile,
        environment=request.environment
    )
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error or result.message
        )
    return result

@router.post("/{service_name}/stop", response_model=ServiceActionResponse)
async def stop_service(
    service_name: str,
    request: ServiceActionRequest = None,
    docker_service: DockerService = Depends(get_docker_service),
    _: dict = Depends(get_current_user)
):
    """Stop a service."""
    request = request or ServiceActionRequest()
    result, warning = docker_service.stop_service(
        service_name,
        force=request.force,
        profile=request.profile
    )

    # Include warning in response if present
    if warning and not request.force:
        result.message = f"{result.message}. Warning: {warning.message}"

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error or result.message
        )
    return result

@router.post("/{service_name}/restart", response_model=ServiceActionResponse)
async def restart_service(
    service_name: str,
    request: ServiceActionRequest = None,
    docker_service: DockerService = Depends(get_docker_service),
    _: dict = Depends(get_current_user)
):
    """Restart a service."""
    request = request or ServiceActionRequest()
    result = docker_service.restart_service(
        service_name,
        profile=request.profile
    )
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error or result.message
        )
    return result

@router.post("/groups/{group_id}/start", response_model=dict)
async def start_service_group(
    group_id: str,
    request: ServiceActionRequest = None,
    docker_service: DockerService = Depends(get_docker_service),
    graph: DependencyGraph = Depends(get_dependency_graph),
    _: dict = Depends(get_current_user)
):
    """Start all services in a group."""
    request = request or ServiceActionRequest()
    groups = graph.get_groups()

    if group_id not in groups:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group '{group_id}' not found"
        )

    services = groups[group_id]["services"]
    results = []

    for service_name in services:
        result = docker_service.start_service(
            service_name,
            profile=request.profile,
            environment=request.environment
        )
        results.append({"service": service_name, "success": result.success})

    return {
        "group": group_id,
        "results": results,
        "success": all(r["success"] for r in results)
    }

@router.post("/groups/{group_id}/stop", response_model=dict)
async def stop_service_group(
    group_id: str,
    request: ServiceActionRequest = None,
    docker_service: DockerService = Depends(get_docker_service),
    graph: DependencyGraph = Depends(get_dependency_graph),
    _: dict = Depends(get_current_user)
):
    """Stop all services in a group."""
    request = request or ServiceActionRequest()
    groups = graph.get_groups()

    if group_id not in groups:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group '{group_id}' not found"
        )

    services = groups[group_id]["services"]
    results = []

    # Stop in reverse order (dependents first)
    for service_name in reversed(services):
        result, _ = docker_service.stop_service(
            service_name,
            force=True,  # Force when stopping group
            profile=request.profile
        )
        results.append({"service": service_name, "success": result.success})

    return {
        "group": group_id,
        "results": results,
        "success": all(r["success"] for r in results)
    }
