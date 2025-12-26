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
