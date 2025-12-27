from pydantic import BaseModel
from typing import List, Dict, Optional
from enum import Enum


class Profile(str, Enum):
    CPU = "cpu"
    GPU_NVIDIA = "gpu-nvidia"
    GPU_AMD = "gpu-amd"
    NONE = "none"


class Environment(str, Enum):
    PRIVATE = "private"
    PUBLIC = "public"


class SetupStatusResponse(BaseModel):
    setup_required: bool
    has_env_file: bool
    has_secrets: bool
    supabase_cloned: bool
    services_running: int
    stack_running: bool = False  # True if any core services are running
    stack_configured: bool = False  # True if user has configured their stack
    missing_secrets: List[str]


class SetupConfigRequest(BaseModel):
    profile: Profile = Profile.CPU
    environment: Environment = Environment.PRIVATE
    enabled_services: List[str] = []
    secrets: Dict[str, str] = {}
    hostnames: Dict[str, str] = {}  # For public environment
    port_overrides: Dict[str, Dict[str, int]] = {}  # service_name -> {port_name -> port}


class SetupStepResult(BaseModel):
    step: str
    status: str  # started, completed, failed
    message: Optional[str] = None
    error: Optional[str] = None


class SetupProgressResponse(BaseModel):
    status: str  # in_progress, completed, failed
    current_step: str
    steps: List[SetupStepResult]
    message: Optional[str] = None
    error: Optional[str] = None


class ServiceSelectionInfo(BaseModel):
    name: str
    display_name: str  # Human-readable name
    group: str
    group_name: str  # Human-readable group name
    description: str
    required: bool
    dependencies: List[str]
    dependency_display: List[str]  # Human-readable dependency names
    profiles: List[str]
    default_enabled: bool
    category: str  # core, infrastructure, optional
    available_for_profile: bool  # Whether available for selected profile


class ServiceSelectionValidation(BaseModel):
    valid: bool
    errors: List[str]
    warnings: List[str]
    auto_enabled: Dict[str, Dict]  # {service: {reason, required_by}}
    total_services: int


class StackConfigResponse(BaseModel):
    profile: str
    environment: str
    enabled_services: List[str]
    setup_completed: bool

    class Config:
        from_attributes = True


# Port configuration schemas
class PortStatus(BaseModel):
    """Status of a single port."""
    port: int
    available: bool
    used_by: Optional[str] = None


class ServicePortScan(BaseModel):
    """Port scan result for a service."""
    service_name: str
    display_name: str
    ports: Dict[str, PortStatus]  # port_name -> status
    all_available: bool
    suggested_ports: Dict[str, int]  # port_name -> suggested alternative


class PortCheckResponse(BaseModel):
    """Response from port availability check."""
    has_conflicts: bool
    services: List[ServicePortScan]
    total_ports_checked: int
    conflicts_count: int


class PortValidation(BaseModel):
    """Validation result for port configuration."""
    valid: bool
    errors: List[str]
    warnings: List[str]
