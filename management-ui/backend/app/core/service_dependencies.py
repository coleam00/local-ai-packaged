"""
Centralized service dependency configuration.
Update this file when adding new services or changing relationships.
"""
from typing import Dict, List, Set
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
