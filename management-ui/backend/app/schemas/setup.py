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
    missing_secrets: List[str]


class SetupConfigRequest(BaseModel):
    profile: Profile = Profile.CPU
    environment: Environment = Environment.PRIVATE
    enabled_services: List[str] = []
    secrets: Dict[str, str] = {}
    hostnames: Dict[str, str] = {}  # For public environment


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
    group: str
    description: str
    required: bool
    dependencies: List[str]
    profiles: List[str]
    default_enabled: bool
