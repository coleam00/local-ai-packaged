# Stage 01: Backend Core & Docker Integration

## Summary
Create the foundation for the management UI backend: Docker client wrapper, compose file parser, dependency graph resolver, and environment manager. This stage establishes the core modules that all other stages build upon.

## Prerequisites
- None (first stage)

## Deliverable
A Python package with tested core modules that can:
- Connect to Docker daemon and list containers
- Parse docker-compose.yml files and extract service definitions
- Build and resolve service dependency graphs
- Read/write/validate .env files

---

## Files to Create

```
management-ui/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── core/
│   │       ├── __init__.py
│   │       ├── docker_client.py
│   │       ├── compose_parser.py
│   │       ├── dependency_graph.py
│   │       ├── env_manager.py
│   │       └── secret_generator.py
│   │
│   └── requirements.txt
```

---

## Task 1: Create Project Structure

**Why**: Establish directory layout and dependencies

**Do**:
```bash
mkdir -p management-ui/backend/app/core
```

Create `management-ui/backend/requirements.txt`:
```
docker>=7.0.0
pyyaml>=6.0
python-dotenv>=1.0.0
pyjwt>=2.8.0
bcrypt>=4.1.0
```

Create `management-ui/backend/app/__init__.py`:
```python
"""Management UI Backend"""
__version__ = "0.1.0"
```

Create `management-ui/backend/app/config.py`:
```python
import os
from pathlib import Path

class Settings:
    COMPOSE_BASE_PATH: str = os.environ.get("COMPOSE_BASE_PATH", "/opt/local-ai-packaged")
    COMPOSE_PROJECT_NAME: str = "localai"
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./data/management.db")
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

settings = Settings()
```

---

## Task 2: Implement Docker Client

**Why**: Wrap docker-py SDK for container management

**File**: `management-ui/backend/app/core/docker_client.py`

```python
import docker
from docker.errors import NotFound, APIError
from typing import List, Dict, Optional, Generator
import subprocess
import os

class DockerClient:
    """Wrapper around docker-py with compose integration."""

    def __init__(self, project: str = "localai", base_path: str = None):
        self.client = docker.from_env()
        self.project = project
        self.base_path = base_path or os.environ.get("COMPOSE_BASE_PATH", ".")

    def list_containers(self, all: bool = True) -> List[Dict]:
        """List all containers in the project."""
        containers = self.client.containers.list(
            all=all,
            filters={"label": f"com.docker.compose.project={self.project}"}
        )
        return [self._container_to_dict(c) for c in containers]

    def get_container(self, service_name: str) -> Optional[Dict]:
        """Get container by service name."""
        containers = self.client.containers.list(
            all=True,
            filters={
                "label": [
                    f"com.docker.compose.project={self.project}",
                    f"com.docker.compose.service={service_name}"
                ]
            }
        )
        return self._container_to_dict(containers[0]) if containers else None

    def get_container_health(self, container_id: str) -> Dict:
        """Get container health status."""
        try:
            container = self.client.containers.get(container_id)
            state = container.attrs.get("State", {})
            health = state.get("Health", {})
            return {
                "status": health.get("Status", "none"),
                "running": state.get("Running", False),
                "failing_streak": health.get("FailingStreak", 0),
            }
        except NotFound:
            return {"status": "not_found", "running": False}

    def stream_logs(self, service_name: str, tail: int = 100) -> Generator[str, None, None]:
        """Stream logs from a container."""
        container_info = self.get_container(service_name)
        if not container_info:
            return

        container = self.client.containers.get(container_info["id"])
        for log in container.logs(stream=True, tail=tail, follow=True):
            yield log.decode("utf-8", errors="replace")

    def compose_up(
        self,
        services: Optional[List[str]] = None,
        profile: Optional[str] = None,
        environment: str = "private",
        detach: bool = True
    ) -> subprocess.CompletedProcess:
        """Run docker compose up."""
        cmd = self._build_compose_command(profile, environment)
        cmd.extend(["up"])
        if detach:
            cmd.append("-d")
        if services:
            cmd.extend(services)
        return subprocess.run(cmd, capture_output=True, text=True, cwd=self.base_path)

    def compose_down(
        self,
        services: Optional[List[str]] = None,
        profile: Optional[str] = None
    ) -> subprocess.CompletedProcess:
        """Run docker compose down/stop."""
        cmd = self._build_compose_command(profile)
        if services:
            cmd.extend(["stop"] + services)
        else:
            cmd.append("down")
        return subprocess.run(cmd, capture_output=True, text=True, cwd=self.base_path)

    def compose_restart(
        self,
        services: List[str],
        profile: Optional[str] = None
    ) -> subprocess.CompletedProcess:
        """Restart specific services."""
        cmd = self._build_compose_command(profile)
        cmd.extend(["restart"] + services)
        return subprocess.run(cmd, capture_output=True, text=True, cwd=self.base_path)

    def _build_compose_command(
        self,
        profile: Optional[str] = None,
        environment: str = "private"
    ) -> List[str]:
        """Build the docker compose command with appropriate files."""
        cmd = ["docker", "compose", "-p", self.project]

        if profile and profile != "none":
            cmd.extend(["--profile", profile])

        cmd.extend(["-f", "docker-compose.yml"])

        if environment == "private":
            cmd.extend(["-f", "docker-compose.override.private.yml"])
        elif environment == "public":
            cmd.extend(["-f", "docker-compose.override.public.yml"])
            cmd.extend(["-f", "docker-compose.override.public.supabase.yml"])

        return cmd

    def _container_to_dict(self, container) -> Dict:
        """Convert container object to dictionary."""
        health = self.get_container_health(container.id)
        return {
            "id": container.short_id,
            "full_id": container.id,
            "name": container.name,
            "service": container.labels.get("com.docker.compose.service"),
            "status": container.status,
            "health": health["status"],
            "running": health["running"],
            "image": container.image.tags[0] if container.image.tags else "unknown",
            "created": container.attrs["Created"],
            "ports": container.ports,
        }

    def is_docker_available(self) -> bool:
        """Check if Docker daemon is accessible."""
        try:
            self.client.ping()
            return True
        except Exception:
            return False
```

**Verify**:
```bash
cd management-ui/backend
python -c "from app.core.docker_client import DockerClient; c = DockerClient(); print(c.list_containers())"
```

---

## Task 3: Implement Compose Parser

**Why**: Extract service definitions and dependencies from compose files

**File**: `management-ui/backend/app/core/compose_parser.py`

```python
import yaml
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class ServiceDefinition:
    name: str
    image: str
    compose_file: str
    profiles: List[str] = field(default_factory=list)
    depends_on: Dict[str, str] = field(default_factory=dict)  # service -> condition
    has_healthcheck: bool = False
    ports: List[str] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)

class ComposeParser:
    """Parse docker-compose.yml files to extract service definitions."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.services: Dict[str, ServiceDefinition] = {}
        self._parse_all()

    def _parse_all(self):
        """Parse main compose file and included files."""
        main_compose = self.base_path / "docker-compose.yml"
        if main_compose.exists():
            self._parse_file(main_compose, "main")

        # Parse Supabase compose if exists
        supabase_compose = self.base_path / "supabase" / "docker" / "docker-compose.yml"
        if supabase_compose.exists():
            self._parse_file(supabase_compose, "supabase")

    def _parse_file(self, filepath: Path, source: str):
        """Parse a single compose file."""
        with open(filepath, 'r') as f:
            try:
                compose = yaml.safe_load(f)
            except yaml.YAMLError as e:
                print(f"Error parsing {filepath}: {e}")
                return

        if not compose or "services" not in compose:
            return

        for name, config in compose.get("services", {}).items():
            if not isinstance(config, dict):
                continue

            # Extract profiles
            profiles = config.get("profiles", [])

            # Extract depends_on
            depends = {}
            deps_config = config.get("depends_on", {})
            if isinstance(deps_config, list):
                depends = {d: "service_started" for d in deps_config}
            elif isinstance(deps_config, dict):
                for dep_name, dep_config in deps_config.items():
                    if isinstance(dep_config, dict):
                        depends[dep_name] = dep_config.get("condition", "service_started")
                    else:
                        depends[dep_name] = "service_started"

            # Extract ports
            ports = []
            for port in config.get("ports", []):
                if isinstance(port, str):
                    ports.append(port)
                elif isinstance(port, dict):
                    ports.append(f"{port.get('published')}:{port.get('target')}")

            self.services[name] = ServiceDefinition(
                name=name,
                image=config.get("image", ""),
                compose_file=source,
                profiles=profiles,
                depends_on=depends,
                has_healthcheck="healthcheck" in config,
                ports=ports,
                environment=self._extract_env(config.get("environment", []))
            )

    def _extract_env(self, env_config: Any) -> Dict[str, str]:
        """Extract environment variables from various formats."""
        if isinstance(env_config, list):
            result = {}
            for item in env_config:
                if "=" in str(item):
                    key, _, value = str(item).partition("=")
                    result[key] = value
                else:
                    result[str(item)] = ""
            return result
        elif isinstance(env_config, dict):
            return {k: str(v) if v else "" for k, v in env_config.items()}
        return {}

    def get_service(self, name: str) -> Optional[ServiceDefinition]:
        """Get a specific service definition."""
        return self.services.get(name)

    def get_all_services(self) -> List[ServiceDefinition]:
        """Get all service definitions."""
        return list(self.services.values())

    def get_services_by_profile(self, profile: str) -> List[ServiceDefinition]:
        """Get services that belong to a specific profile."""
        return [s for s in self.services.values() if profile in s.profiles]

    def get_services_without_profile(self) -> List[ServiceDefinition]:
        """Get services that have no profile (always run)."""
        return [s for s in self.services.values() if not s.profiles]

    def to_dict(self) -> Dict[str, Dict]:
        """Export all services as dictionary."""
        return {
            name: {
                "name": svc.name,
                "image": svc.image,
                "compose_file": svc.compose_file,
                "profiles": svc.profiles,
                "depends_on": svc.depends_on,
                "has_healthcheck": svc.has_healthcheck,
                "ports": svc.ports,
            }
            for name, svc in self.services.items()
        }
```

**Verify**:
```bash
python -c "from app.core.compose_parser import ComposeParser; p = ComposeParser('/opt/local-ai-packaged'); print(len(p.services), 'services found')"
```

---

## Task 4: Implement Dependency Graph

**Why**: Resolve service start order and detect dependents

**File**: `management-ui/backend/app/core/dependency_graph.py`

```python
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
from .compose_parser import ComposeParser, ServiceDefinition

SERVICE_GROUPS = {
    "supabase": {
        "name": "Supabase",
        "services": ["db", "kong", "auth", "rest", "realtime", "storage",
                     "studio", "meta", "functions", "analytics", "vector",
                     "imgproxy", "supavisor"],
        "description": "Supabase backend-as-a-service"
    },
    "core_ai": {
        "name": "AI Services",
        "services": ["ollama-cpu", "ollama-gpu", "ollama-gpu-amd",
                     "open-webui", "flowise"],
        "description": "Core AI inference and interfaces"
    },
    "workflow": {
        "name": "Workflow",
        "services": ["n8n", "n8n-import"],
        "description": "Workflow automation"
    },
    "database": {
        "name": "Databases",
        "services": ["postgres", "qdrant", "neo4j"],
        "description": "Vector and graph databases"
    },
    "observability": {
        "name": "Observability",
        "services": ["langfuse-web", "langfuse-worker", "clickhouse", "minio"],
        "description": "LLM observability and tracing"
    },
    "infrastructure": {
        "name": "Infrastructure",
        "services": ["caddy", "redis", "searxng"],
        "description": "Reverse proxy, caching, search"
    }
}

class DependencyGraph:
    """Manages service dependency resolution."""

    def __init__(self, parser: ComposeParser):
        self.parser = parser
        self.services = parser.services

    def get_service_group(self, service_name: str) -> str:
        """Determine which group a service belongs to."""
        for group_id, group_info in SERVICE_GROUPS.items():
            if service_name in group_info["services"]:
                return group_id
        return "other"

    def get_start_order(self, services: List[str]) -> List[List[str]]:
        """
        Get ordered batches for starting services.
        Returns list of batches that can be started in parallel.
        """
        result = []
        remaining = set(services)
        resolved = set()

        # Add services that are already running or not in our list
        all_service_names = set(self.services.keys())
        for svc in all_service_names:
            if svc not in services:
                resolved.add(svc)

        max_iterations = len(services) + 1
        iteration = 0

        while remaining and iteration < max_iterations:
            batch = []

            for service in list(remaining):
                svc_def = self.services.get(service)
                if not svc_def:
                    # Unknown service, add to batch
                    batch.append(service)
                    continue

                # Check if all dependencies are resolved
                deps_satisfied = all(
                    dep in resolved
                    for dep in svc_def.depends_on.keys()
                )

                if deps_satisfied:
                    batch.append(service)

            if not batch:
                # Circular dependency or missing dependencies
                raise ValueError(
                    f"Cannot resolve dependencies for: {remaining}. "
                    f"Check for circular dependencies."
                )

            result.append(sorted(batch))
            for service in batch:
                remaining.discard(service)
                resolved.add(service)

            iteration += 1

        return result

    def get_dependents(self, service: str) -> Set[str]:
        """Get all services that depend on the given service (directly or transitively)."""
        dependents = set()

        for name, svc_def in self.services.items():
            if service in svc_def.depends_on:
                dependents.add(name)
                # Recursively get dependents of dependents
                dependents.update(self.get_dependents(name))

        return dependents

    def get_dependencies(self, service: str) -> Set[str]:
        """Get all services that the given service depends on (directly or transitively)."""
        svc_def = self.services.get(service)
        if not svc_def:
            return set()

        deps = set(svc_def.depends_on.keys())
        for dep in list(deps):
            deps.update(self.get_dependencies(dep))

        return deps

    def get_required_services(self, services: List[str]) -> List[str]:
        """
        Given a list of services, return all services needed including dependencies.
        """
        required = set(services)
        for service in services:
            required.update(self.get_dependencies(service))
        return list(required)

    def get_stop_warning(self, service: str) -> Optional[Dict]:
        """
        Check if stopping a service would affect others.
        Returns warning info if there are dependents.
        """
        dependents = self.get_dependents(service)
        if dependents:
            return {
                "service": service,
                "dependents": list(dependents),
                "message": f"Stopping {service} will affect: {', '.join(sorted(dependents))}"
            }
        return None

    def to_visualization_format(self) -> Dict:
        """Export graph for frontend visualization (react-flow compatible)."""
        nodes = []
        edges = []

        for name, svc_def in self.services.items():
            nodes.append({
                "id": name,
                "data": {
                    "label": name,
                    "group": self.get_service_group(name),
                    "profiles": svc_def.profiles,
                    "hasHealthcheck": svc_def.has_healthcheck,
                    "composeFile": svc_def.compose_file,
                }
            })

            for dep, condition in svc_def.depends_on.items():
                edges.append({
                    "id": f"{dep}->{name}",
                    "source": dep,
                    "target": name,
                    "data": {"condition": condition}
                })

        return {"nodes": nodes, "edges": edges}

    def get_groups(self) -> Dict:
        """Get service groups with their services."""
        result = {}
        for group_id, group_info in SERVICE_GROUPS.items():
            # Only include services that actually exist
            existing = [s for s in group_info["services"] if s in self.services]
            if existing:
                result[group_id] = {
                    "name": group_info["name"],
                    "description": group_info["description"],
                    "services": existing
                }
        return result
```

**Verify**:
```bash
python -c "
from app.core.compose_parser import ComposeParser
from app.core.dependency_graph import DependencyGraph
p = ComposeParser('/opt/local-ai-packaged')
g = DependencyGraph(p)
print('Groups:', list(g.get_groups().keys()))
print('n8n dependencies:', g.get_dependencies('n8n'))
"
```

---

## Task 5: Implement Environment Manager

**Why**: Manage .env file with validation and backup

**File**: `management-ui/backend/app/core/env_manager.py`

```python
from typing import Dict, List, Optional, Any
from pathlib import Path
import re
import shutil
from datetime import datetime

# Configuration schema for validation
ENV_SCHEMA = {
    "N8N_ENCRYPTION_KEY": {
        "category": "n8n",
        "is_secret": True,
        "is_required": True,
        "description": "Encryption key for n8n credentials (64 hex chars)",
        "validation_regex": r"^[a-f0-9]{64}$",
        "generate": "hex_32"
    },
    "N8N_USER_MANAGEMENT_JWT_SECRET": {
        "category": "n8n",
        "is_secret": True,
        "is_required": True,
        "description": "JWT secret for n8n user management",
        "generate": "hex_32"
    },
    "POSTGRES_PASSWORD": {
        "category": "supabase",
        "is_secret": True,
        "is_required": True,
        "description": "PostgreSQL password (avoid @ symbol)",
        "validation_regex": r"^[^@]{8,}$"
    },
    "JWT_SECRET": {
        "category": "supabase",
        "is_secret": True,
        "is_required": True,
        "description": "Supabase JWT secret (min 32 chars)",
        "validation_regex": r"^.{32,}$"
    },
    "ANON_KEY": {
        "category": "supabase",
        "is_secret": True,
        "is_required": True,
        "description": "Supabase anonymous key (JWT)",
        "generate": "supabase_jwt_anon"
    },
    "SERVICE_ROLE_KEY": {
        "category": "supabase",
        "is_secret": True,
        "is_required": True,
        "description": "Supabase service role key (JWT)",
        "generate": "supabase_jwt_service"
    },
    "NEO4J_AUTH": {
        "category": "neo4j",
        "is_secret": True,
        "is_required": True,
        "description": "Neo4j auth (format: username/password)",
        "validation_regex": r"^[^/]+/.+$"
    },
    "CLICKHOUSE_PASSWORD": {
        "category": "langfuse",
        "is_secret": True,
        "is_required": True,
        "description": "ClickHouse password"
    },
    "MINIO_ROOT_PASSWORD": {
        "category": "langfuse",
        "is_secret": True,
        "is_required": True,
        "description": "MinIO root password"
    },
    "LANGFUSE_SALT": {
        "category": "langfuse",
        "is_secret": True,
        "is_required": True,
        "description": "Langfuse encryption salt"
    },
    "NEXTAUTH_SECRET": {
        "category": "langfuse",
        "is_secret": True,
        "is_required": True,
        "description": "NextAuth secret for Langfuse"
    },
    "ENCRYPTION_KEY": {
        "category": "langfuse",
        "is_secret": True,
        "is_required": True,
        "description": "Langfuse encryption key (64 hex chars)",
        "generate": "hex_32"
    },
}

class EnvManager:
    """Manages .env file operations with validation."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.env_file = self.base_path / ".env"
        self.env_example = self.base_path / ".env.example"
        self.backup_dir = self.base_path / ".env_backups"

    def load(self) -> Dict[str, str]:
        """Load current .env file."""
        if not self.env_file.exists():
            return {}

        env = {}
        with open(self.env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, _, value = line.partition('=')
                    env[key.strip()] = value.strip()
        return env

    def save(self, env: Dict[str, str], backup: bool = True) -> str:
        """Save .env file with optional backup. Returns backup path if created."""
        backup_path = None
        if backup and self.env_file.exists():
            backup_path = self._create_backup()

        # Try to preserve structure from example file
        lines = []
        written_keys = set()

        if self.env_example.exists():
            with open(self.env_example, 'r') as f:
                for line in f:
                    stripped = line.strip()
                    if '=' in stripped and not stripped.startswith('#'):
                        key = stripped.split('=')[0].strip()
                        if key in env:
                            lines.append(f"{key}={env[key]}\n")
                            written_keys.add(key)
                        else:
                            lines.append(line)
                    else:
                        lines.append(line)

        # Add any remaining new variables
        for key, value in env.items():
            if key not in written_keys:
                lines.append(f"{key}={value}\n")

        with open(self.env_file, 'w') as f:
            f.writelines(lines)

        # Copy to Supabase directory
        self._sync_to_supabase()

        return backup_path or ""

    def _sync_to_supabase(self):
        """Copy .env to supabase/docker/.env"""
        supabase_env = self.base_path / "supabase" / "docker" / ".env"
        if supabase_env.parent.exists() and self.env_file.exists():
            shutil.copy(self.env_file, supabase_env)

    def validate(self, env: Dict[str, str]) -> List[Dict]:
        """Validate environment variables against schema."""
        errors = []

        for var_name, schema in ENV_SCHEMA.items():
            value = env.get(var_name, "")

            # Check required
            if schema.get("is_required") and not value:
                errors.append({
                    "variable": var_name,
                    "error": "required",
                    "message": f"{var_name} is required"
                })
                continue

            # Check if using placeholder value
            if value and any(placeholder in value.lower() for placeholder in
                           ["secret", "password", "your-", "change", "example"]):
                errors.append({
                    "variable": var_name,
                    "error": "placeholder",
                    "message": f"{var_name} appears to be a placeholder value"
                })

            # Check regex validation
            if value and schema.get("validation_regex"):
                if not re.match(schema["validation_regex"], value):
                    errors.append({
                        "variable": var_name,
                        "error": "format",
                        "message": f"{var_name} has invalid format"
                    })

        return errors

    def get_masked(self) -> Dict[str, Any]:
        """Get env vars with secrets masked for display."""
        env = self.load()
        result = {}

        for key, value in env.items():
            schema = ENV_SCHEMA.get(key, {})
            if schema.get("is_secret", False) and value:
                # Show first 4 and last 4 chars if long enough
                if len(value) > 12:
                    result[key] = f"{value[:4]}...{value[-4:]}"
                else:
                    result[key] = "********"
            else:
                result[key] = value

        return result

    def get_schema(self) -> Dict:
        """Get the configuration schema for the UI."""
        return ENV_SCHEMA

    def get_categories(self) -> Dict[str, List[str]]:
        """Get variables grouped by category."""
        categories = {}
        for var_name, schema in ENV_SCHEMA.items():
            cat = schema.get("category", "other")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(var_name)
        return categories

    def _create_backup(self) -> str:
        """Create timestamped backup of .env file."""
        self.backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f".env.{timestamp}"
        shutil.copy(self.env_file, backup_path)
        return str(backup_path)

    def list_backups(self) -> List[Dict]:
        """List available backups."""
        if not self.backup_dir.exists():
            return []

        backups = []
        for f in sorted(self.backup_dir.glob(".env.*"), reverse=True):
            backups.append({
                "filename": f.name,
                "path": str(f),
                "created": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })
        return backups[:20]  # Keep last 20

    def restore_backup(self, filename: str) -> None:
        """Restore from a backup file."""
        backup_path = self.backup_dir / filename
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup {filename} not found")

        self._create_backup()  # Backup current before restore
        shutil.copy(backup_path, self.env_file)
        self._sync_to_supabase()

    def env_file_exists(self) -> bool:
        """Check if .env file exists."""
        return self.env_file.exists()
```

---

## Task 6: Implement Secret Generator

**Why**: Generate secure secrets for initial setup

**File**: `management-ui/backend/app/core/secret_generator.py`

```python
import secrets
import jwt
from datetime import datetime
from typing import Dict

def generate_hex_key(bytes_length: int = 32) -> str:
    """Generate a random hex key."""
    return secrets.token_hex(bytes_length)

def generate_safe_password(length: int = 24) -> str:
    """Generate a secure password without problematic characters."""
    # Avoid @, %, and other chars that can cause issues in connection strings
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!#$^&*-_=+"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_supabase_jwt(role: str, jwt_secret: str) -> str:
    """Generate Supabase JWT key (anon or service_role)."""
    payload = {
        "role": role,
        "iss": "supabase-local",
        "iat": int(datetime.now().timestamp()),
        "exp": int(datetime(2099, 12, 31).timestamp())
    }
    return jwt.encode(payload, jwt_secret, algorithm="HS256")

def generate_all_secrets() -> Dict[str, str]:
    """Generate all required secrets for the stack."""
    jwt_secret = generate_hex_key(32)

    return {
        # n8n
        "N8N_ENCRYPTION_KEY": generate_hex_key(32),
        "N8N_USER_MANAGEMENT_JWT_SECRET": generate_hex_key(32),

        # Supabase core
        "POSTGRES_PASSWORD": generate_safe_password(24),
        "JWT_SECRET": jwt_secret,
        "ANON_KEY": generate_supabase_jwt("anon", jwt_secret),
        "SERVICE_ROLE_KEY": generate_supabase_jwt("service_role", jwt_secret),
        "SECRET_KEY_BASE": generate_hex_key(32),
        "VAULT_ENC_KEY": generate_safe_password(32),

        # Supabase dashboard
        "DASHBOARD_USERNAME": "admin",
        "DASHBOARD_PASSWORD": generate_safe_password(16),

        # Supabase pooler
        "POOLER_TENANT_ID": f"tenant-{secrets.token_hex(8)}",

        # Neo4j
        "NEO4J_AUTH": f"neo4j/{generate_safe_password(16)}",

        # Langfuse
        "CLICKHOUSE_PASSWORD": generate_safe_password(20),
        "MINIO_ROOT_PASSWORD": generate_safe_password(20),
        "LANGFUSE_SALT": generate_hex_key(16),
        "NEXTAUTH_SECRET": generate_hex_key(32),
        "ENCRYPTION_KEY": generate_hex_key(32),

        # Logflare
        "LOGFLARE_PUBLIC_ACCESS_TOKEN": generate_hex_key(32),
        "LOGFLARE_PRIVATE_ACCESS_TOKEN": generate_hex_key(32),
    }

def generate_missing_secrets(current_env: Dict[str, str]) -> Dict[str, str]:
    """Generate only the secrets that are missing or have placeholder values."""
    all_secrets = generate_all_secrets()
    result = {}

    placeholders = ["secret", "password", "your-", "change", "example", "super-secret"]

    for key, new_value in all_secrets.items():
        current_value = current_env.get(key, "")

        # Generate if missing or is a placeholder
        is_placeholder = any(p in current_value.lower() for p in placeholders) if current_value else True

        if not current_value or is_placeholder:
            result[key] = new_value

    return result
```

**Verify**:
```bash
python -c "from app.core.secret_generator import generate_all_secrets; s = generate_all_secrets(); print('Generated', len(s), 'secrets')"
```

---

## Task 7: Create Core __init__.py

**File**: `management-ui/backend/app/core/__init__.py`

```python
from .docker_client import DockerClient
from .compose_parser import ComposeParser
from .dependency_graph import DependencyGraph
from .env_manager import EnvManager
from .secret_generator import generate_all_secrets, generate_missing_secrets

__all__ = [
    "DockerClient",
    "ComposeParser",
    "DependencyGraph",
    "EnvManager",
    "generate_all_secrets",
    "generate_missing_secrets",
]
```

---

## Validation

### Test Commands
```bash
cd management-ui/backend

# Install dependencies
pip install -r requirements.txt

# Test Docker client
python -c "
from app.core import DockerClient
client = DockerClient(base_path='/opt/local-ai-packaged')
print('Docker available:', client.is_docker_available())
containers = client.list_containers()
print(f'Found {len(containers)} containers')
"

# Test Compose parser
python -c "
from app.core import ComposeParser
parser = ComposeParser('/opt/local-ai-packaged')
print(f'Parsed {len(parser.services)} services')
for name in list(parser.services.keys())[:5]:
    print(f'  - {name}')
"

# Test Dependency graph
python -c "
from app.core import ComposeParser, DependencyGraph
parser = ComposeParser('/opt/local-ai-packaged')
graph = DependencyGraph(parser)
print('Service groups:', list(graph.get_groups().keys()))
print('n8n depends on:', graph.get_dependencies('n8n'))
print('langfuse-web depends on:', graph.get_dependencies('langfuse-web'))
"

# Test Env manager
python -c "
from app.core import EnvManager
em = EnvManager('/opt/local-ai-packaged')
print('Env file exists:', em.env_file_exists())
env = em.load()
print(f'Loaded {len(env)} variables')
errors = em.validate(env)
print(f'Validation errors: {len(errors)}')
"

# Test Secret generator
python -c "
from app.core import generate_all_secrets
secrets = generate_all_secrets()
print(f'Generated {len(secrets)} secrets')
for key in list(secrets.keys())[:3]:
    print(f'  {key}: {secrets[key][:20]}...')
"
```

### Success Criteria
- [ ] All imports work without errors
- [ ] DockerClient can list containers
- [ ] ComposeParser finds 20+ services
- [ ] DependencyGraph resolves n8n dependencies correctly
- [ ] EnvManager can load/validate .env
- [ ] SecretGenerator produces valid secrets

---

## Next Stage
Proceed to `02-auth-database.md` to add authentication and database layer.
