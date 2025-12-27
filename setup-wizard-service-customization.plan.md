# Plan: Setup Wizard Service Customization with Dependency Management

## Summary

Extend the setup wizard to allow users to select which services they want to run, with intelligent dependency management that automatically enables required dependencies and informs users of relationships. The wizard should only display when the stack is NOT already running. Dependencies are defined in a centralized, easily maintainable configuration.

## External Research

### Documentation
- [Docker Docs - Control startup order](https://docs.docker.com/compose/how-tos/startup-order/) - Official guide
  - Key: `depends_on` with `condition: service_healthy` is the 2025 best practice
  - `restart: true` ensures dependent services restart when dependencies restart
- [Docker Compose Best Practices 2025](https://toxigon.com/docker-compose-best-practices-2025)
  - Key: Keep dependencies minimal, use health checks, test thoroughly

### Gotchas & Best Practices
- `depends_on` only controls startup order, not readiness - use `condition: service_healthy`
- `required: false` (since Docker Compose 2.20.0) allows optional dependencies
- External service dependencies need custom retry logic (wait-for scripts)
- Current docker-compose files have some missing dependencies that need validation

## Patterns to Mirror

### ServiceGroup Component Pattern
```typescript
// FROM: management-ui/frontend/src/pages/Services.tsx:178-206
// This is how grouped services are displayed with actions:
<ServiceGroup
  key={groupId}
  group={groupData}
  isActionInProgress={actionInProgress === `group:${groupId}`}
  onStartGroup={() => startGroup(groupId)}
  onStopGroup={() => stopGroup(groupId)}
>
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
    {groupServices.map((service) => (
      <ServiceCard key={service.name} service={service} ... />
    ))}
  </div>
</ServiceGroup>
```

### Step Component Pattern
```typescript
// FROM: management-ui/frontend/src/components/setup/ProfileStep.tsx:41-76
// This is how wizard step components are structured:
interface ProfileStepProps {
  value: string;
  onChange: (value: string) => void;
}

export const ProfileStep: React.FC<ProfileStepProps> = ({ value, onChange }) => {
  return (
    <div>
      <h3 className="text-lg font-semibold text-white mb-2">Title</h3>
      <p className="text-gray-400 mb-6">Description</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Selection cards */}
      </div>
    </div>
  );
};
```

### Dependency Graph Pattern
```python
# FROM: management-ui/backend/app/core/dependency_graph.py:40-54
# This is how service groups are defined:
SERVICE_GROUPS = {
    "supabase": {
        "name": "Supabase",
        "services": ["db", "kong", "auth", ...],
        "description": "Supabase backend-as-a-service"
    },
    # ... more groups
}
```

### Schema Pattern
```python
# FROM: management-ui/backend/app/schemas/setup.py:50-57
# This is how service info is structured:
class ServiceSelectionInfo(BaseModel):
    name: str
    group: str
    description: str
    required: bool
    dependencies: List[str]
    profiles: List[str]
    default_enabled: bool
```

### API Route Pattern
```python
# FROM: management-ui/backend/app/api/routes/setup.py:27-33
@router.get("/services", response_model=List[ServiceSelectionInfo])
async def get_available_services(
    setup_service: SetupService = Depends(get_setup_service),
    _: dict = Depends(get_current_user)
):
    """Get available services for selection."""
    return setup_service.get_available_services()
```

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `backend/app/core/service_dependencies.py` | CREATE | Centralized dependency configuration for easy updates |
| `backend/app/core/dependency_graph.py` | UPDATE | Use centralized deps, add validation methods |
| `backend/app/schemas/setup.py` | UPDATE | Add enhanced service info with dependency details |
| `backend/app/services/setup_service.py` | UPDATE | Better dependency resolution, running check |
| `backend/app/api/routes/setup.py` | UPDATE | Add endpoint for dependency validation |
| `frontend/src/components/setup/ServicesStep.tsx` | CREATE | New step for service selection |
| `frontend/src/components/setup/SetupWizard.tsx` | UPDATE | Add services step, update step flow |
| `frontend/src/components/setup/ConfirmStep.tsx` | UPDATE | Show selected services summary |
| `frontend/src/store/authStore.ts` | UPDATE | Add services running check |
| `frontend/src/api/setup.ts` | CREATE | API client for setup endpoints |
| `frontend/src/App.tsx` | UPDATE | Show wizard only when stack not running |

## NOT Building

- Drag-and-drop service reordering
- Custom profile creation
- Service configuration editing (env vars, ports)
- Real-time dependency graph visualization (Dependencies page exists for this)
- Service health monitoring in wizard (Dashboard handles this)
- Multi-tenancy or user-specific service configs

## Tasks

### Task 1: Create Centralized Service Dependencies Configuration

**Why**: Dependencies are currently scattered. A single source of truth makes updates fast and prevents drift between docker-compose and UI.

**Mirror**: `backend/app/core/dependency_graph.py:5-39` (SERVICE_GROUPS pattern)

**File**: `management-ui/backend/app/core/service_dependencies.py`

**Do**:
```python
"""
Centralized service dependency configuration.
Update this file when adding new services or changing relationships.
"""
from typing import Dict, List, Set, NamedTuple
from dataclasses import dataclass, field

@dataclass
class ServiceConfig:
    """Configuration for a single service."""
    name: str
    display_name: str
    description: str
    group: str
    dependencies: List[str] = field(default_factory=list)
    required: bool = False  # Core infrastructure, cannot be disabled
    default_enabled: bool = True
    profiles: List[str] = field(default_factory=list)  # Empty = always run
    category: str = "optional"  # core, infrastructure, optional

# Service dependency definitions
# Format: service_name -> ServiceConfig
# Dependencies listed here OVERRIDE docker-compose depends_on for UI purposes

SERVICE_CONFIGS: Dict[str, ServiceConfig] = {
    # === SUPABASE CORE (required, cannot disable) ===
    "vector": ServiceConfig(
        name="vector",
        display_name="Vector",
        description="Log aggregation for Supabase services",
        group="supabase",
        dependencies=[],
        required=True,
        category="core"
    ),
    "db": ServiceConfig(
        name="db",
        display_name="Database",
        description="PostgreSQL database (Supabase)",
        group="supabase",
        dependencies=["vector"],
        required=True,
        category="core"
    ),
    "analytics": ServiceConfig(
        name="analytics",
        display_name="Analytics",
        description="Logflare analytics backend",
        group="supabase",
        dependencies=["db"],
        required=True,
        category="core"
    ),
    "kong": ServiceConfig(
        name="kong",
        display_name="Kong API Gateway",
        description="API gateway for Supabase services",
        group="supabase",
        dependencies=["analytics"],
        required=True,
        category="core"
    ),

    # === SUPABASE SERVICES (optional) ===
    "auth": ServiceConfig(
        name="auth",
        display_name="Auth (GoTrue)",
        description="Authentication and user management",
        group="supabase",
        dependencies=["db", "analytics"],
        default_enabled=True,
        category="infrastructure"
    ),
    "rest": ServiceConfig(
        name="rest",
        display_name="REST API (PostgREST)",
        description="Auto-generated REST API from database",
        group="supabase",
        dependencies=["db", "analytics"],
        default_enabled=True,
        category="infrastructure"
    ),
    "realtime": ServiceConfig(
        name="realtime",
        display_name="Realtime",
        description="WebSocket subscriptions for database changes",
        group="supabase",
        dependencies=["db", "analytics"],
        default_enabled=True,
        category="infrastructure"
    ),
    "storage": ServiceConfig(
        name="storage",
        display_name="Storage",
        description="File storage with S3-compatible API",
        group="supabase",
        dependencies=["db", "rest", "imgproxy"],
        default_enabled=True,
        category="infrastructure"
    ),
    "imgproxy": ServiceConfig(
        name="imgproxy",
        display_name="Image Proxy",
        description="On-the-fly image processing",
        group="supabase",
        dependencies=[],
        default_enabled=True,
        category="infrastructure"
    ),
    "meta": ServiceConfig(
        name="meta",
        display_name="Postgres Meta",
        description="Database metadata API",
        group="supabase",
        dependencies=["db", "analytics"],
        default_enabled=True,
        category="infrastructure"
    ),
    "functions": ServiceConfig(
        name="functions",
        display_name="Edge Functions",
        description="Serverless Deno functions",
        group="supabase",
        dependencies=["analytics"],
        default_enabled=True,
        category="optional"
    ),
    "studio": ServiceConfig(
        name="studio",
        display_name="Studio",
        description="Supabase dashboard UI",
        group="supabase",
        dependencies=["analytics"],
        default_enabled=True,
        category="optional"
    ),
    "supavisor": ServiceConfig(
        name="supavisor",
        display_name="Supavisor (Pooler)",
        description="Connection pooler for PostgreSQL",
        group="supabase",
        dependencies=["db", "analytics"],
        default_enabled=True,
        category="infrastructure"
    ),

    # === AI SERVICES ===
    "ollama-cpu": ServiceConfig(
        name="ollama-cpu",
        display_name="Ollama (CPU)",
        description="Local LLM inference on CPU",
        group="core_ai",
        dependencies=[],
        profiles=["cpu"],
        default_enabled=True,
        category="optional"
    ),
    "ollama-gpu": ServiceConfig(
        name="ollama-gpu",
        display_name="Ollama (NVIDIA GPU)",
        description="Local LLM inference with NVIDIA CUDA",
        group="core_ai",
        dependencies=[],
        profiles=["gpu-nvidia"],
        default_enabled=True,
        category="optional"
    ),
    "ollama-gpu-amd": ServiceConfig(
        name="ollama-gpu-amd",
        display_name="Ollama (AMD GPU)",
        description="Local LLM inference with AMD ROCm",
        group="core_ai",
        dependencies=[],
        profiles=["gpu-amd"],
        default_enabled=True,
        category="optional"
    ),
    "open-webui": ServiceConfig(
        name="open-webui",
        display_name="Open WebUI",
        description="Chat interface for LLMs",
        group="core_ai",
        dependencies=[],  # Connects to Ollama but doesn't require it
        default_enabled=True,
        category="optional"
    ),
    "flowise": ServiceConfig(
        name="flowise",
        display_name="Flowise",
        description="Visual LLM flow builder",
        group="core_ai",
        dependencies=[],
        default_enabled=True,
        category="optional"
    ),

    # === WORKFLOW ===
    "n8n-import": ServiceConfig(
        name="n8n-import",
        display_name="n8n Import",
        description="Import default workflows (runs once)",
        group="workflow",
        dependencies=["db"],
        default_enabled=True,
        category="infrastructure"
    ),
    "n8n": ServiceConfig(
        name="n8n",
        display_name="n8n",
        description="Workflow automation platform",
        group="workflow",
        dependencies=["n8n-import"],
        default_enabled=True,
        category="optional"
    ),

    # === DATABASES ===
    "qdrant": ServiceConfig(
        name="qdrant",
        display_name="Qdrant",
        description="Vector database for embeddings",
        group="database",
        dependencies=[],
        default_enabled=True,
        category="optional"
    ),
    "neo4j": ServiceConfig(
        name="neo4j",
        display_name="Neo4j",
        description="Graph database",
        group="database",
        dependencies=[],
        default_enabled=True,
        category="optional"
    ),

    # === OBSERVABILITY (Langfuse) ===
    "postgres": ServiceConfig(
        name="postgres",
        display_name="Postgres (Langfuse)",
        description="PostgreSQL for Langfuse",
        group="observability",
        dependencies=[],
        default_enabled=True,
        category="infrastructure"
    ),
    "redis": ServiceConfig(
        name="redis",
        display_name="Redis/Valkey",
        description="In-memory cache and message broker",
        group="infrastructure",
        dependencies=[],
        default_enabled=True,
        category="infrastructure"
    ),
    "clickhouse": ServiceConfig(
        name="clickhouse",
        display_name="ClickHouse",
        description="Analytics database for Langfuse",
        group="observability",
        dependencies=[],
        default_enabled=True,
        category="infrastructure"
    ),
    "minio": ServiceConfig(
        name="minio",
        display_name="MinIO",
        description="S3-compatible object storage for Langfuse",
        group="observability",
        dependencies=[],
        default_enabled=True,
        category="infrastructure"
    ),
    "langfuse-worker": ServiceConfig(
        name="langfuse-worker",
        display_name="Langfuse Worker",
        description="Background worker for Langfuse",
        group="observability",
        dependencies=["postgres", "minio", "redis", "clickhouse"],
        default_enabled=True,
        category="optional"
    ),
    "langfuse-web": ServiceConfig(
        name="langfuse-web",
        display_name="Langfuse",
        description="LLM observability and tracing",
        group="observability",
        dependencies=["postgres", "minio", "redis", "clickhouse"],
        default_enabled=True,
        category="optional"
    ),

    # === INFRASTRUCTURE ===
    "caddy": ServiceConfig(
        name="caddy",
        display_name="Caddy",
        description="Reverse proxy with automatic HTTPS",
        group="infrastructure",
        dependencies=[],
        required=True,
        category="core"
    ),
    "searxng": ServiceConfig(
        name="searxng",
        display_name="SearXNG",
        description="Privacy-respecting metasearch engine",
        group="infrastructure",
        dependencies=[],
        default_enabled=True,
        category="optional"
    ),
}

# Group definitions with metadata
SERVICE_GROUPS = {
    "supabase": {
        "name": "Supabase",
        "description": "Backend-as-a-service platform",
        "icon": "database",
        "order": 1
    },
    "core_ai": {
        "name": "AI Services",
        "description": "Local LLM inference and interfaces",
        "icon": "brain",
        "order": 2
    },
    "workflow": {
        "name": "Workflow Automation",
        "description": "Workflow and automation tools",
        "icon": "workflow",
        "order": 3
    },
    "database": {
        "name": "Additional Databases",
        "description": "Vector and graph databases",
        "icon": "database",
        "order": 4
    },
    "observability": {
        "name": "Observability",
        "description": "LLM tracing and monitoring",
        "icon": "chart",
        "order": 5
    },
    "infrastructure": {
        "name": "Infrastructure",
        "description": "Core infrastructure services",
        "icon": "server",
        "order": 6
    }
}


def get_all_dependencies(service_name: str, visited: Set[str] = None) -> Set[str]:
    """Get all transitive dependencies for a service."""
    if visited is None:
        visited = set()

    if service_name in visited:
        return set()

    visited.add(service_name)
    config = SERVICE_CONFIGS.get(service_name)
    if not config:
        return set()

    deps = set(config.dependencies)
    for dep in list(deps):
        deps.update(get_all_dependencies(dep, visited.copy()))

    return deps


def get_required_for_selection(selected: List[str]) -> Dict[str, List[str]]:
    """
    Given a list of selected services, return all required services
    with info about why each is needed.

    Returns: {service_name: [list of services that require it]}
    """
    required: Dict[str, List[str]] = {}

    for service in selected:
        deps = get_all_dependencies(service)
        for dep in deps:
            if dep not in required:
                required[dep] = []
            required[dep].append(service)

    # Add always-required services
    for name, config in SERVICE_CONFIGS.items():
        if config.required and name not in required:
            required[name] = ["(core infrastructure)"]

    return required


def validate_selection(selected: List[str], profile: str) -> Dict:
    """
    Validate a service selection.
    Returns: {valid: bool, errors: [], warnings: [], auto_enabled: {}}
    """
    errors = []
    warnings = []
    auto_enabled = {}

    # Check profile-specific services
    profile_ollama_map = {
        "cpu": "ollama-cpu",
        "gpu-nvidia": "ollama-gpu",
        "gpu-amd": "ollama-gpu-amd"
    }

    # Get required dependencies
    required = get_required_for_selection(selected)

    for dep, requesters in required.items():
        if dep not in selected:
            config = SERVICE_CONFIGS.get(dep)
            if config:
                auto_enabled[dep] = {
                    "reason": f"Required by: {', '.join(requesters[:3])}",
                    "required_by": requesters
                }

    # Check for services without matching profile
    for service in selected:
        config = SERVICE_CONFIGS.get(service)
        if config and config.profiles:
            if profile not in config.profiles and profile != "none":
                warnings.append(
                    f"{config.display_name} requires profile {config.profiles}, "
                    f"but {profile} was selected"
                )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "auto_enabled": auto_enabled,
        "total_services": len(selected) + len(auto_enabled)
    }
```

**Don't**:
- Don't duplicate logic that exists in docker-compose
- Don't add UI-specific fields (icons, colors)

**Verify**: `python -c "from app.core.service_dependencies import validate_selection; print(validate_selection(['n8n', 'langfuse-web'], 'cpu'))"`

---

### Task 2: Update Dependency Graph to Use Centralized Config

**Why**: The existing DependencyGraph reads from docker-compose but we need to use our centralized config for accurate dependency info.

**Mirror**: Current `dependency_graph.py` patterns

**File**: `management-ui/backend/app/core/dependency_graph.py`

**Do**:
Update `get_service_group` and add methods to use centralized config:
```python
from .service_dependencies import SERVICE_CONFIGS, SERVICE_GROUPS, get_required_for_selection, validate_selection

# Add at class level:
def get_service_config(self, service_name: str):
    """Get centralized config for a service."""
    return SERVICE_CONFIGS.get(service_name)

def get_enhanced_service_info(self, service_name: str, profile: str):
    """Get service info combining docker-compose and centralized config."""
    compose_def = self.services.get(service_name)
    central_config = SERVICE_CONFIGS.get(service_name)

    if not compose_def:
        return None

    return {
        "name": service_name,
        "display_name": central_config.display_name if central_config else service_name,
        "description": central_config.description if central_config else f"From {compose_def.compose_file}",
        "group": central_config.group if central_config else self.get_service_group(service_name),
        "dependencies": list(central_config.dependencies) if central_config else list(compose_def.depends_on.keys()),
        "required": central_config.required if central_config else False,
        "default_enabled": central_config.default_enabled if central_config else True,
        "profiles": central_config.profiles if central_config else compose_def.profiles,
        "category": central_config.category if central_config else "optional",
        "available_for_profile": (
            not central_config.profiles or
            profile in central_config.profiles or
            profile == "none"
        ) if central_config else True
    }

def validate_service_selection(self, selected: List[str], profile: str):
    """Validate a service selection with the centralized config."""
    return validate_selection(selected, profile)
```

**Don't**:
- Don't remove existing methods (needed for visualization)

**Verify**: Read file and check methods exist

---

### Task 3: Update Setup Schemas

**Why**: Need enhanced info for frontend to display dependencies and auto-selections.

**Mirror**: `schemas/setup.py:50-57`

**File**: `management-ui/backend/app/schemas/setup.py`

**Do**:
```python
# Add new fields to ServiceSelectionInfo
class ServiceSelectionInfo(BaseModel):
    name: str
    display_name: str  # NEW: Human-readable name
    group: str
    group_name: str  # NEW: Human-readable group name
    description: str
    required: bool
    dependencies: List[str]
    dependency_display: List[str]  # NEW: Human-readable dependency names
    profiles: List[str]
    default_enabled: bool
    category: str  # NEW: core, infrastructure, optional
    available_for_profile: bool  # NEW: Whether available for selected profile

# Add new response for validation
class ServiceSelectionValidation(BaseModel):
    valid: bool
    errors: List[str]
    warnings: List[str]
    auto_enabled: Dict[str, Dict]  # {service: {reason, required_by}}
    total_services: int

# Update SetupStatusResponse
class SetupStatusResponse(BaseModel):
    setup_required: bool
    has_env_file: bool
    has_secrets: bool
    supabase_cloned: bool
    services_running: int
    stack_running: bool  # NEW: True if any core services are running
    missing_secrets: List[str]
```

**Don't**:
- Don't break existing consumers of these schemas

**Verify**: `python -c "from app.schemas.setup import ServiceSelectionInfo; print('OK')"`

---

### Task 4: Update Setup Service

**Why**: Need to provide enhanced service info and check if stack is running.

**Mirror**: `services/setup_service.py:59-83`

**File**: `management-ui/backend/app/services/setup_service.py`

**Do**:
```python
# Update get_status to include stack_running check
def get_status(self) -> SetupStatusResponse:
    """Check current setup status."""
    # ... existing code ...

    # Check if core services are running
    stack_running = False
    try:
        containers = self.docker_client.list_containers()
        core_services = {"db", "kong", "caddy", "vector"}
        running_services = {c.get("service") for c in containers if c.get("status") == "running"}
        stack_running = len(core_services & running_services) >= 2  # At least 2 core services
    except Exception:
        pass

    return SetupStatusResponse(
        # ... existing fields ...
        stack_running=stack_running
    )

# Update get_available_services
def get_available_services(self, profile: str = "cpu") -> List[ServiceSelectionInfo]:
    """Get list of services available for selection with enhanced info."""
    from ..core.service_dependencies import SERVICE_CONFIGS, SERVICE_GROUPS

    try:
        parser = ComposeParser(str(self.base_path))
        graph = DependencyGraph(parser)
    except Exception:
        return []

    services = []
    for name, svc_def in parser.services.items():
        # Skip init containers
        if "import" in name and name != "n8n-import":
            continue
        if "pull-llama" in name:
            continue

        info = graph.get_enhanced_service_info(name, profile)
        if not info:
            continue

        config = SERVICE_CONFIGS.get(name)
        group_meta = SERVICE_GROUPS.get(info["group"], {})

        # Get human-readable dependency names
        dep_display = []
        for dep in info["dependencies"]:
            dep_config = SERVICE_CONFIGS.get(dep)
            dep_display.append(dep_config.display_name if dep_config else dep)

        services.append(ServiceSelectionInfo(
            name=name,
            display_name=info["display_name"],
            group=info["group"],
            group_name=group_meta.get("name", info["group"]),
            description=info["description"],
            required=info["required"],
            dependencies=info["dependencies"],
            dependency_display=dep_display,
            profiles=info["profiles"],
            default_enabled=info["default_enabled"],
            category=info["category"],
            available_for_profile=info["available_for_profile"]
        ))

    return services

# Add new method for validation
def validate_selection(self, selected: List[str], profile: str) -> Dict:
    """Validate a service selection."""
    from ..core.service_dependencies import validate_selection
    return validate_selection(selected, profile)
```

**Don't**:
- Don't break the existing `run_full_setup` method

**Verify**: Run backend and test `/setup/services?profile=cpu` endpoint

---

### Task 5: Update Setup Routes

**Why**: Need endpoint for validation and update services endpoint.

**Mirror**: `api/routes/setup.py` patterns

**File**: `management-ui/backend/app/api/routes/setup.py`

**Do**:
```python
from ...schemas.setup import ServiceSelectionValidation
from typing import Optional

# Update get_available_services to accept profile
@router.get("/services", response_model=List[ServiceSelectionInfo])
async def get_available_services(
    profile: str = "cpu",
    setup_service: SetupService = Depends(get_setup_service),
    _: dict = Depends(get_current_user)
):
    """Get available services for selection."""
    return setup_service.get_available_services(profile)

# Add validation endpoint
@router.post("/validate-selection", response_model=ServiceSelectionValidation)
async def validate_service_selection(
    selected: List[str],
    profile: str = "cpu",
    setup_service: SetupService = Depends(get_setup_service),
    _: dict = Depends(get_current_user)
):
    """Validate a service selection and get auto-enabled dependencies."""
    result = setup_service.validate_selection(selected, profile)
    return ServiceSelectionValidation(**result)
```

**Don't**:
- Don't require auth for status endpoint (needs to work before login)

**Verify**: `curl -X POST http://localhost:8000/api/setup/validate-selection -d '{"selected":["n8n"],"profile":"cpu"}'`

---

### Task 6: Create Setup API Client

**Why**: Need frontend API client for new setup endpoints.

**Mirror**: `api/auth.ts` patterns

**File**: `management-ui/frontend/src/api/setup.ts`

**Do**:
```typescript
import { apiClient } from './client';

export interface ServiceInfo {
  name: string;
  display_name: string;
  group: string;
  group_name: string;
  description: string;
  required: boolean;
  dependencies: string[];
  dependency_display: string[];
  profiles: string[];
  default_enabled: boolean;
  category: string;
  available_for_profile: boolean;
}

export interface SelectionValidation {
  valid: boolean;
  errors: string[];
  warnings: string[];
  auto_enabled: Record<string, { reason: string; required_by: string[] }>;
  total_services: number;
}

export interface SetupStatus {
  setup_required: boolean;
  has_env_file: boolean;
  has_secrets: boolean;
  supabase_cloned: boolean;
  services_running: number;
  stack_running: boolean;
  missing_secrets: string[];
}

export const setupApi = {
  async getStatus(): Promise<SetupStatus> {
    const response = await apiClient.get<SetupStatus>('/setup/status');
    return response.data;
  },

  async getServices(profile: string): Promise<ServiceInfo[]> {
    const response = await apiClient.get<ServiceInfo[]>('/setup/services', {
      params: { profile }
    });
    return response.data;
  },

  async validateSelection(selected: string[], profile: string): Promise<SelectionValidation> {
    const response = await apiClient.post<SelectionValidation>('/setup/validate-selection', {
      selected,
      profile
    });
    return response.data;
  },

  async generateSecrets(): Promise<Record<string, string>> {
    const response = await apiClient.post<{ secrets: Record<string, string> }>('/setup/generate-secrets');
    return response.data.secrets;
  },

  async complete(config: {
    profile: string;
    environment: string;
    secrets: Record<string, string>;
    enabled_services: string[];
  }): Promise<{ status: string; error?: string }> {
    const response = await apiClient.post('/setup/complete', config);
    return response.data;
  }
};
```

**Don't**:
- Don't duplicate types that exist elsewhere

**Verify**: Import in a component and check no TypeScript errors

---

### Task 7: Create ServicesStep Component

**Why**: Main feature - allows users to select which services to run.

**Mirror**: `components/setup/ProfileStep.tsx` and `pages/Services.tsx` patterns

**File**: `management-ui/frontend/src/components/setup/ServicesStep.tsx`

**Do**:
```typescript
import React, { useEffect, useState, useMemo } from 'react';
import { Card } from '../common/Card';
import { setupApi, ServiceInfo, SelectionValidation } from '../../api/setup';
import {
  Check, AlertTriangle, Info, ChevronDown, ChevronRight,
  Database, Brain, Workflow, Server, BarChart3, Layers
} from 'lucide-react';

interface ServicesStepProps {
  profile: string;
  value: string[];
  onChange: (value: string[]) => void;
}

const groupIcons: Record<string, React.ElementType> = {
  supabase: Database,
  core_ai: Brain,
  workflow: Workflow,
  database: Database,
  observability: BarChart3,
  infrastructure: Server,
};

export const ServicesStep: React.FC<ServicesStepProps> = ({ profile, value, onChange }) => {
  const [services, setServices] = useState<ServiceInfo[]>([]);
  const [validation, setValidation] = useState<SelectionValidation | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['core_ai', 'workflow']));

  // Fetch services when profile changes
  useEffect(() => {
    const fetchServices = async () => {
      setLoading(true);
      try {
        const data = await setupApi.getServices(profile);
        setServices(data);

        // Auto-select defaults if nothing selected
        if (value.length === 0) {
          const defaults = data
            .filter(s => s.default_enabled && s.available_for_profile && !s.required)
            .map(s => s.name);
          onChange(defaults);
        }
      } catch (error) {
        console.error('Failed to fetch services:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchServices();
  }, [profile]);

  // Validate selection when it changes
  useEffect(() => {
    const validate = async () => {
      if (value.length === 0) return;
      try {
        const result = await setupApi.validateSelection(value, profile);
        setValidation(result);
      } catch (error) {
        console.error('Validation failed:', error);
      }
    };
    validate();
  }, [value, profile]);

  // Group services
  const groupedServices = useMemo(() => {
    const groups = new Map<string, ServiceInfo[]>();
    for (const service of services) {
      if (!groups.has(service.group)) {
        groups.set(service.group, []);
      }
      groups.get(service.group)!.push(service);
    }
    return groups;
  }, [services]);

  const toggleService = (serviceName: string) => {
    const service = services.find(s => s.name === serviceName);
    if (!service || service.required) return;

    if (value.includes(serviceName)) {
      onChange(value.filter(s => s !== serviceName));
    } else {
      onChange([...value, serviceName]);
    }
  };

  const toggleGroup = (groupId: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  };

  const isServiceEnabled = (service: ServiceInfo) => {
    if (service.required) return true;
    if (value.includes(service.name)) return true;
    if (validation?.auto_enabled[service.name]) return true;
    return false;
  };

  const getServiceStatus = (service: ServiceInfo) => {
    if (service.required) return 'required';
    if (validation?.auto_enabled[service.name]) return 'auto';
    if (value.includes(service.name)) return 'selected';
    return 'disabled';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div>
      <h3 className="text-lg font-semibold text-white mb-2">Select Services</h3>
      <p className="text-gray-400 mb-4">
        Choose which services to run. Dependencies are automatically included.
      </p>

      {/* Validation warnings */}
      {validation?.warnings && validation.warnings.length > 0 && (
        <div className="mb-4 p-3 bg-yellow-900/30 border border-yellow-700 rounded-lg">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-yellow-400">
              {validation.warnings.map((w, i) => (
                <p key={i}>{w}</p>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Auto-enabled info */}
      {validation?.auto_enabled && Object.keys(validation.auto_enabled).length > 0 && (
        <div className="mb-4 p-3 bg-blue-900/30 border border-blue-700 rounded-lg">
          <div className="flex items-start gap-2">
            <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-300">
              <p className="font-medium mb-1">Auto-enabled dependencies:</p>
              {Object.entries(validation.auto_enabled).map(([name, info]) => (
                <p key={name} className="text-blue-400/80">
                  {services.find(s => s.name === name)?.display_name || name}: {info.reason}
                </p>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Service groups */}
      <div className="space-y-4">
        {Array.from(groupedServices.entries())
          .sort((a, b) => {
            const order = ['supabase', 'core_ai', 'workflow', 'database', 'observability', 'infrastructure'];
            return order.indexOf(a[0]) - order.indexOf(b[0]);
          })
          .map(([groupId, groupServices]) => {
            const Icon = groupIcons[groupId] || Layers;
            const isExpanded = expandedGroups.has(groupId);
            const enabledCount = groupServices.filter(s => isServiceEnabled(s)).length;
            const firstService = groupServices[0];

            return (
              <div key={groupId} className="border border-gray-700 rounded-lg overflow-hidden">
                <button
                  onClick={() => toggleGroup(groupId)}
                  className="w-full flex items-center justify-between p-4 bg-gray-800 hover:bg-gray-750 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <Icon className="w-5 h-5 text-blue-400" />
                    <div className="text-left">
                      <h4 className="font-medium text-white">{firstService?.group_name || groupId}</h4>
                      <p className="text-xs text-gray-500">
                        {enabledCount} of {groupServices.length} services enabled
                      </p>
                    </div>
                  </div>
                  {isExpanded ? (
                    <ChevronDown className="w-5 h-5 text-gray-400" />
                  ) : (
                    <ChevronRight className="w-5 h-5 text-gray-400" />
                  )}
                </button>

                {isExpanded && (
                  <div className="p-4 bg-gray-900 space-y-2">
                    {groupServices
                      .filter(s => s.available_for_profile)
                      .map(service => {
                        const status = getServiceStatus(service);
                        return (
                          <div
                            key={service.name}
                            onClick={() => toggleService(service.name)}
                            className={`
                              flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-colors
                              ${status === 'selected' ? 'bg-blue-900/30 border border-blue-700' : ''}
                              ${status === 'auto' ? 'bg-purple-900/20 border border-purple-700/50' : ''}
                              ${status === 'required' ? 'bg-green-900/20 border border-green-700/50 cursor-not-allowed' : ''}
                              ${status === 'disabled' ? 'bg-gray-800 border border-gray-700 hover:border-gray-600' : ''}
                            `}
                          >
                            <div className={`
                              w-5 h-5 rounded flex items-center justify-center flex-shrink-0 mt-0.5
                              ${status === 'disabled' ? 'border-2 border-gray-600' : 'bg-green-600'}
                            `}>
                              {status !== 'disabled' && <Check className="w-3 h-3 text-white" />}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="font-medium text-white">
                                  {service.display_name}
                                </span>
                                {status === 'required' && (
                                  <span className="text-xs px-1.5 py-0.5 bg-green-900/50 text-green-400 rounded">
                                    Required
                                  </span>
                                )}
                                {status === 'auto' && (
                                  <span className="text-xs px-1.5 py-0.5 bg-purple-900/50 text-purple-400 rounded">
                                    Auto
                                  </span>
                                )}
                              </div>
                              <p className="text-sm text-gray-400 mt-0.5">{service.description}</p>
                              {service.dependencies.length > 0 && (
                                <p className="text-xs text-gray-500 mt-1">
                                  Requires: {service.dependency_display.join(', ')}
                                </p>
                              )}
                            </div>
                          </div>
                        );
                      })}
                  </div>
                )}
              </div>
            );
          })}
      </div>

      {/* Summary */}
      <div className="mt-6 p-4 bg-gray-800 rounded-lg">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">
            {validation?.total_services || value.length} services will be started
          </span>
          <span className="text-gray-500">
            {Object.keys(validation?.auto_enabled || {}).length} auto-enabled
          </span>
        </div>
      </div>
    </div>
  );
};
```

**Don't**:
- Don't allow toggling required services
- Don't fetch services on every render

**Verify**: Visual check in browser, services load for each profile

---

### Task 8: Update SetupWizard to Include Services Step

**Why**: Need to integrate the new ServicesStep into the wizard flow.

**Mirror**: Current SetupWizard structure

**File**: `management-ui/frontend/src/components/setup/SetupWizard.tsx`

**Do**:
1. Import `ServicesStep`:
```typescript
import { ServicesStep } from './ServicesStep';
```

2. Update STEPS array:
```typescript
const STEPS = ['profile', 'services', 'environment', 'secrets', 'confirm'] as const;
const STEP_LABELS = ['Profile', 'Services', 'Environment', 'Secrets', 'Confirm'];
```

3. Add services case to `renderStep`:
```typescript
case 'services':
  return (
    <ServicesStep
      profile={config.profile}
      value={config.enabled_services}
      onChange={(enabled_services) => setConfig({ ...config, enabled_services })}
    />
  );
```

4. Update `canProceed` to validate services:
```typescript
case 'services':
  return config.enabled_services.length > 0 || true; // Allow proceeding with defaults
```

**Don't**:
- Don't change existing step logic

**Verify**: Navigate through wizard, services step appears after profile

---

### Task 9: Update ConfirmStep to Show Services

**Why**: Users need to see which services will be started before confirming.

**Mirror**: Current ConfirmStep structure

**File**: `management-ui/frontend/src/components/setup/ConfirmStep.tsx`

**Do**:
```typescript
// Update interface
interface ConfirmStepProps {
  config: {
    profile: string;
    environment: string;
    secrets: Record<string, string>;
    enabled_services: string[];
  };
}

// Add services display after secrets section
<div className="flex items-start gap-3">
  <Layers className="w-5 h-5 text-cyan-400" />
  <div>
    <span className="text-gray-400 text-sm">Services:</span>
    <span className="ml-2 font-medium text-white">
      {config.enabled_services.length} selected
    </span>
    {config.enabled_services.length > 0 && (
      <p className="text-xs text-gray-500 mt-1">
        {config.enabled_services.slice(0, 5).join(', ')}
        {config.enabled_services.length > 5 && ` +${config.enabled_services.length - 5} more`}
      </p>
    )}
  </div>
</div>
```

**Don't**:
- Don't show full service list (too long)

**Verify**: Confirm step shows service count

---

### Task 10: Update Auth Store for Stack Running Check

**Why**: App.tsx needs to know if stack is running to decide whether to show wizard.

**Mirror**: Current authStore patterns

**File**: `management-ui/frontend/src/store/authStore.ts`

**Do**:
```typescript
// Add to interface
stackRunning: boolean;

// Add to initial state
stackRunning: false,

// Update checkSetupStatus
checkSetupStatus: async () => {
  try {
    const status = await authApi.getSetupStatus();
    // Also check stack status
    let stackRunning = false;
    try {
      const stackStatus = await setupApi.getStatus();
      stackRunning = stackStatus.stack_running;
    } catch {}

    set({
      setupRequired: status.setup_required,
      stackRunning,
      isLoading: false
    });
    return status.setup_required;
  } catch {
    set({ isLoading: false });
    return false;
  }
},
```

Also add import for setupApi.

**Don't**:
- Don't block on stack status check (non-critical)

**Verify**: Store has stackRunning property

---

### Task 11: Update App.tsx for Conditional Wizard Display

**Why**: Setup wizard should only show when stack is NOT running.

**Mirror**: Current App.tsx routing logic

**File**: `management-ui/frontend/src/App.tsx`

**Do**:
```typescript
// Get stackRunning from store
const { checkAuth, checkSetupStatus, isLoading, setupRequired, stackRunning } = useAuthStore();

// Update wizard routing condition
if (setupRequired && !stackRunning) {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/setup" element={<Setup />} />
        <Route path="*" element={<Navigate to="/setup" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
```

**Don't**:
- Don't change authenticated routes

**Verify**: When stack running, no redirect to setup wizard

---

## Validation Strategy

### Automated Checks
- [ ] `cd management-ui/backend && python -m pytest` - Backend tests pass
- [ ] `cd management-ui/frontend && npm run build` - Frontend builds
- [ ] `cd management-ui/frontend && npm run lint` - No lint errors

### New Tests to Write

| Test File | Test Case | What It Validates |
|-----------|-----------|-------------------|
| `backend/tests/test_service_dependencies.py` | `test_get_all_dependencies` | Transitive deps calculated correctly |
| `backend/tests/test_service_dependencies.py` | `test_validate_selection` | Validation returns correct auto-enabled |
| `backend/tests/test_service_dependencies.py` | `test_required_services` | Required services always included |

### Manual/E2E Validation

1. **Fresh install test**:
   - Delete `.env` and database
   - Start management UI
   - Verify wizard appears
   - Complete all steps
   - Verify stack starts with selected services

2. **Dependency test**:
   - Select only `n8n` in wizard
   - Verify `n8n-import`, `db` (Supabase) shown as auto-enabled
   - Complete setup
   - Verify all dependent services start

3. **Profile test**:
   - Select `cpu` profile
   - Verify `ollama-gpu` not available
   - Select `gpu-nvidia` profile
   - Verify `ollama-gpu` available, `ollama-cpu` not

4. **Running stack test**:
   - Start stack manually
   - Refresh page
   - Verify wizard does NOT appear
   - Navigate to `/setup-wizard`
   - Verify can access (for reconfiguration)

### Edge Cases

- [ ] No services selected: Should show at least required services
- [ ] Profile change mid-wizard: Services should reload
- [ ] All optional services disabled: Stack should still start with core
- [ ] Network error fetching services: Graceful error handling
- [ ] Very slow validation: Loading state shown

### Regression Check

- [ ] Existing Services page still works
- [ ] Existing Dependencies page still works
- [ ] Login/logout flow unchanged
- [ ] Dashboard loads correctly after setup

## Risks

1. **Docker-compose dependency mismatch**: Centralized config may drift from actual docker-compose. Mitigate by documenting update process.

2. **Performance**: Loading all services for selection could be slow. Mitigate by caching.

3. **Complexity**: Dependency auto-selection may confuse users. Mitigate by clear UI messaging.

4. **Breaking existing setups**: Changes to setup flow may break existing installations. Mitigate by careful schema evolution.
