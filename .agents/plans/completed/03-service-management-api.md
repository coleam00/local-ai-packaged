# Stage 03: Service Management API

## Summary
Add REST API endpoints for listing, starting, stopping, and restarting Docker services. This stage makes the backend fully functional for service control via API.

## Prerequisites
- Stage 01 completed (core modules)
- Stage 02 completed (auth & database)

## Deliverable
- GET /api/services - List all services with status
- GET /api/services/{name} - Get service details
- POST /api/services/{name}/start - Start service
- POST /api/services/{name}/stop - Stop service
- POST /api/services/{name}/restart - Restart service
- GET /api/services/dependencies - Get dependency graph
- GET /api/services/groups - Get service groups

---

## Files to Create/Modify

```
management-ui/backend/app/
├── schemas/
│   └── service.py           # NEW: Service schemas
├── services/
│   ├── __init__.py          # NEW
│   └── docker_service.py    # NEW: Service operations
└── api/routes/
    └── services.py          # NEW: Service endpoints
```

---

## Task 1: Create Service Schemas

**File**: `management-ui/backend/app/schemas/service.py`

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum

class ServiceStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    STOPPING = "stopping"
    RESTARTING = "restarting"
    ERROR = "error"
    NOT_CREATED = "not_created"

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    NONE = "none"
    UNKNOWN = "unknown"

class ServiceInfo(BaseModel):
    name: str
    status: ServiceStatus
    health: HealthStatus
    image: Optional[str] = None
    container_id: Optional[str] = None
    ports: List[str] = []
    group: str
    compose_file: str
    profiles: List[str] = []
    has_healthcheck: bool = False
    depends_on: Dict[str, str] = {}

class ServiceListResponse(BaseModel):
    services: List[ServiceInfo]
    total: int

class ServiceDetailResponse(ServiceInfo):
    environment: Dict[str, str] = {}
    created: Optional[str] = None
    dependents: List[str] = []
    dependencies: List[str] = []

class ServiceActionRequest(BaseModel):
    profile: Optional[str] = None
    environment: str = "private"
    force: bool = False  # Force stop even if has dependents

class ServiceActionResponse(BaseModel):
    success: bool
    message: str
    service: str
    action: str
    output: Optional[str] = None
    error: Optional[str] = None

class DependencyWarning(BaseModel):
    service: str
    dependents: List[str]
    message: str

class DependencyGraphResponse(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]

class ServiceGroupInfo(BaseModel):
    id: str
    name: str
    description: str
    services: List[str]
    running_count: int = 0
    total_count: int = 0

class ServiceGroupsResponse(BaseModel):
    groups: List[ServiceGroupInfo]
```

Update `management-ui/backend/app/schemas/__init__.py`:
```python
from .auth import *
from .service import *
```

---

## Task 2: Create Docker Service Layer

**File**: `management-ui/backend/app/services/__init__.py`
```python
from .docker_service import DockerService

__all__ = ["DockerService"]
```

**File**: `management-ui/backend/app/services/docker_service.py`

```python
from typing import List, Dict, Optional, Tuple
from ..core.docker_client import DockerClient
from ..core.compose_parser import ComposeParser
from ..core.dependency_graph import DependencyGraph
from ..schemas.service import (
    ServiceInfo, ServiceStatus, HealthStatus,
    ServiceDetailResponse, ServiceActionResponse, DependencyWarning
)

class DockerService:
    """Service layer for Docker operations."""

    def __init__(
        self,
        docker_client: DockerClient,
        parser: ComposeParser,
        graph: DependencyGraph
    ):
        self.docker = docker_client
        self.parser = parser
        self.graph = graph

    def list_services(self) -> List[ServiceInfo]:
        """List all services with their current status."""
        # Get running containers
        containers = self.docker.list_containers(all=True)
        container_map = {c["service"]: c for c in containers if c.get("service")}

        services = []
        for name, svc_def in self.parser.services.items():
            container = container_map.get(name)

            if container:
                status = self._map_container_status(container["status"])
                health = self._map_health_status(container["health"])
                image = container.get("image")
                container_id = container.get("id")
                ports = self._format_ports(container.get("ports", {}))
            else:
                status = ServiceStatus.NOT_CREATED
                health = HealthStatus.NONE
                image = svc_def.image
                container_id = None
                ports = svc_def.ports

            services.append(ServiceInfo(
                name=name,
                status=status,
                health=health,
                image=image,
                container_id=container_id,
                ports=ports,
                group=self.graph.get_service_group(name),
                compose_file=svc_def.compose_file,
                profiles=svc_def.profiles,
                has_healthcheck=svc_def.has_healthcheck,
                depends_on=svc_def.depends_on
            ))

        return sorted(services, key=lambda s: (s.group, s.name))

    def get_service(self, name: str) -> Optional[ServiceDetailResponse]:
        """Get detailed info about a specific service."""
        svc_def = self.parser.get_service(name)
        if not svc_def:
            return None

        container = self.docker.get_container(name)

        if container:
            status = self._map_container_status(container["status"])
            health = self._map_health_status(container["health"])
            image = container.get("image")
            container_id = container.get("id")
            ports = self._format_ports(container.get("ports", {}))
            created = container.get("created")
        else:
            status = ServiceStatus.NOT_CREATED
            health = HealthStatus.NONE
            image = svc_def.image
            container_id = None
            ports = svc_def.ports
            created = None

        return ServiceDetailResponse(
            name=name,
            status=status,
            health=health,
            image=image,
            container_id=container_id,
            ports=ports,
            group=self.graph.get_service_group(name),
            compose_file=svc_def.compose_file,
            profiles=svc_def.profiles,
            has_healthcheck=svc_def.has_healthcheck,
            depends_on=svc_def.depends_on,
            environment=svc_def.environment,
            created=created,
            dependents=list(self.graph.get_dependents(name)),
            dependencies=list(self.graph.get_dependencies(name))
        )

    def start_service(
        self,
        name: str,
        profile: Optional[str] = None,
        environment: str = "private"
    ) -> ServiceActionResponse:
        """Start a service and its dependencies."""
        svc_def = self.parser.get_service(name)
        if not svc_def:
            return ServiceActionResponse(
                success=False,
                message=f"Service '{name}' not found",
                service=name,
                action="start"
            )

        # Check if service requires a specific profile
        if svc_def.profiles and profile not in svc_def.profiles:
            if not profile:
                profile = svc_def.profiles[0]

        try:
            result = self.docker.compose_up(
                services=[name],
                profile=profile,
                environment=environment
            )

            if result.returncode == 0:
                return ServiceActionResponse(
                    success=True,
                    message=f"Service '{name}' started successfully",
                    service=name,
                    action="start",
                    output=result.stdout
                )
            else:
                return ServiceActionResponse(
                    success=False,
                    message=f"Failed to start service '{name}'",
                    service=name,
                    action="start",
                    error=result.stderr
                )
        except Exception as e:
            return ServiceActionResponse(
                success=False,
                message=str(e),
                service=name,
                action="start",
                error=str(e)
            )

    def stop_service(
        self,
        name: str,
        force: bool = False,
        profile: Optional[str] = None
    ) -> Tuple[ServiceActionResponse, Optional[DependencyWarning]]:
        """Stop a service, with warning about dependents."""
        svc_def = self.parser.get_service(name)
        if not svc_def:
            return ServiceActionResponse(
                success=False,
                message=f"Service '{name}' not found",
                service=name,
                action="stop"
            ), None

        # Check for dependents
        warning = None
        dependents = self.graph.get_dependents(name)
        if dependents and not force:
            warning = DependencyWarning(
                service=name,
                dependents=list(dependents),
                message=f"Stopping {name} will affect: {', '.join(sorted(dependents))}"
            )
            # Still proceed but return warning

        try:
            result = self.docker.compose_down(
                services=[name],
                profile=profile
            )

            if result.returncode == 0:
                return ServiceActionResponse(
                    success=True,
                    message=f"Service '{name}' stopped successfully",
                    service=name,
                    action="stop",
                    output=result.stdout
                ), warning
            else:
                return ServiceActionResponse(
                    success=False,
                    message=f"Failed to stop service '{name}'",
                    service=name,
                    action="stop",
                    error=result.stderr
                ), warning
        except Exception as e:
            return ServiceActionResponse(
                success=False,
                message=str(e),
                service=name,
                action="stop",
                error=str(e)
            ), warning

    def restart_service(
        self,
        name: str,
        profile: Optional[str] = None
    ) -> ServiceActionResponse:
        """Restart a service."""
        svc_def = self.parser.get_service(name)
        if not svc_def:
            return ServiceActionResponse(
                success=False,
                message=f"Service '{name}' not found",
                service=name,
                action="restart"
            )

        try:
            result = self.docker.compose_restart(
                services=[name],
                profile=profile
            )

            if result.returncode == 0:
                return ServiceActionResponse(
                    success=True,
                    message=f"Service '{name}' restarted successfully",
                    service=name,
                    action="restart",
                    output=result.stdout
                )
            else:
                return ServiceActionResponse(
                    success=False,
                    message=f"Failed to restart service '{name}'",
                    service=name,
                    action="restart",
                    error=result.stderr
                )
        except Exception as e:
            return ServiceActionResponse(
                success=False,
                message=str(e),
                service=name,
                action="restart",
                error=str(e)
            )

    def get_groups_with_status(self) -> Dict[str, Dict]:
        """Get service groups with running status."""
        groups = self.graph.get_groups()
        services = self.list_services()
        service_status = {s.name: s.status for s in services}

        result = {}
        for group_id, group_info in groups.items():
            running = sum(
                1 for s in group_info["services"]
                if service_status.get(s) == ServiceStatus.RUNNING
            )
            result[group_id] = {
                **group_info,
                "id": group_id,
                "running_count": running,
                "total_count": len(group_info["services"])
            }

        return result

    def _map_container_status(self, status: str) -> ServiceStatus:
        """Map Docker container status to ServiceStatus enum."""
        status_lower = status.lower()
        if status_lower == "running":
            return ServiceStatus.RUNNING
        elif status_lower in ("exited", "dead", "created"):
            return ServiceStatus.STOPPED
        elif status_lower == "restarting":
            return ServiceStatus.RESTARTING
        elif status_lower == "paused":
            return ServiceStatus.STOPPED
        else:
            return ServiceStatus.ERROR

    def _map_health_status(self, health: str) -> HealthStatus:
        """Map Docker health status to HealthStatus enum."""
        health_lower = health.lower() if health else "none"
        if health_lower == "healthy":
            return HealthStatus.HEALTHY
        elif health_lower == "unhealthy":
            return HealthStatus.UNHEALTHY
        elif health_lower == "starting":
            return HealthStatus.STARTING
        elif health_lower == "none":
            return HealthStatus.NONE
        else:
            return HealthStatus.UNKNOWN

    def _format_ports(self, ports: Dict) -> List[str]:
        """Format port mappings to string list."""
        result = []
        for container_port, host_bindings in ports.items():
            if host_bindings:
                for binding in host_bindings:
                    host_port = binding.get("HostPort", "")
                    host_ip = binding.get("HostIp", "0.0.0.0")
                    result.append(f"{host_ip}:{host_port}->{container_port}")
            else:
                result.append(container_port)
        return result
```

---

## Task 3: Create Service Routes

**File**: `management-ui/backend/app/api/routes/services.py`

```python
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
    get_current_user
)

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
```

---

## Task 4: Update API Router

**File**: `management-ui/backend/app/api/routes/__init__.py` (update)

```python
from fastapi import APIRouter
from .auth import router as auth_router
from .services import router as services_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(services_router, prefix="/services", tags=["services"])
```

---

## Validation

### Start the Server
```bash
cd management-ui/backend
python -m uvicorn app.main:app --reload --port 9000
```

### Test Endpoints (get token first)
```bash
# Login to get token
TOKEN=$(curl -s -X POST http://localhost:9000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "adminpass123"}' | jq -r '.access_token')

# List all services
curl -s http://localhost:9000/api/services \
  -H "Authorization: Bearer $TOKEN" | jq '.total'

# Get service groups
curl -s http://localhost:9000/api/services/groups \
  -H "Authorization: Bearer $TOKEN" | jq '.groups[].name'

# Get dependency graph
curl -s http://localhost:9000/api/services/dependencies \
  -H "Authorization: Bearer $TOKEN" | jq '.nodes | length'

# Get specific service
curl -s http://localhost:9000/api/services/n8n \
  -H "Authorization: Bearer $TOKEN" | jq

# Start a service (careful - this actually starts it!)
curl -X POST http://localhost:9000/api/services/redis/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"environment": "private"}' | jq

# Stop a service
curl -X POST http://localhost:9000/api/services/redis/stop \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Success Criteria
- [ ] GET /api/services returns list of all services with status
- [ ] GET /api/services/groups returns groups with running counts
- [ ] GET /api/services/dependencies returns graph data
- [ ] GET /api/services/{name} returns service details
- [ ] POST /api/services/{name}/start starts the service
- [ ] POST /api/services/{name}/stop stops the service with warning for dependents
- [ ] POST /api/services/{name}/restart restarts the service
- [ ] All endpoints require authentication

---

## Next Stage
Proceed to `04-frontend-foundation.md` to create the React frontend shell.
