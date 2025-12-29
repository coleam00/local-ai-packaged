# Plan: Local Storage Path Support (Feature #7 - GitHub Issue #156)

## Summary

This feature enables users to use local filesystem bind mounts instead of Docker named volumes for service data storage. The implementation adds environment variables to toggle between volume types per service, a new "Storage" step in the setup wizard for path validation and configuration, a migration tool to copy data from existing Docker volumes to local paths, and comprehensive permissions handling guidance. This gives users easier access to their data files and enables use of standard backup tools (rsync, Borg, etc.) without Docker-specific commands.

## External Research

### Documentation
- [Docker Volumes Documentation](https://docs.docker.com/engine/storage/volumes/) - Official guide on named volumes
  - Key: Volumes are stored in `/var/lib/docker/volumes/<volume_name>/_data`
- [Docker Bind Mounts Documentation](https://docs.docker.com/engine/storage/bind-mounts/) - Official bind mount guide
  - Key: Bind mounts depend on host directory structure and permissions
- [Docker Compose Volumes Reference](https://docs.docker.com/reference/compose-file/volumes/) - Syntax for volumes in compose files

### Gotchas & Best Practices
- **Permissions**: Container processes often run as non-root users. Bind mount directories must have correct ownership (e.g., UID 1000 for n8n, UID 101 for ClickHouse)
- **Path existence**: Unlike named volumes, bind mount paths must exist before container starts
- **SELinux**: On SELinux-enabled systems, may need `:z` or `:Z` suffix on volume mounts
- **Relative vs absolute paths**: Docker Compose treats paths starting with `.` or `..` as bind mounts, absolute paths or names as volumes
- **Migration approach**: Use rsync with `-a` flag to preserve ownership/permissions when copying from volumes to bind mounts. Stop containers first to prevent data corruption.
- **Volume data location**: Docker stores named volume data at `/var/lib/docker/volumes/<volume_name>/_data`

## Patterns to Mirror

### 1. Environment Variable Pattern in .env.example
```python
# FROM: /opt/local-ai-packaged/.env.example:85-111
# Optional configuration section pattern

# Everything below this point is optional.
# Default values will suffice unless you need more features/customization.

############
# Optional SearXNG Config
# If you run a very small or a very large instance, you might want to change...
############

# SEARXNG_UWSGI_WORKERS=4
# SEARXNG_UWSGI_THREADS=4
```

### 2. EnvManager Schema Pattern
```python
# FROM: /opt/local-ai-packaged/management-ui/backend/app/core/env_manager.py:8-20
ENV_SCHEMA = {
    "N8N_ENCRYPTION_KEY": {
        "category": "n8n",
        "is_secret": True,
        "is_required": True,
        "description": "Encryption key for n8n credentials (64 hex chars)",
        "validation_regex": r"^[a-f0-9]{64}$",
        "generate": "hex_32"
    },
    # ... more entries
}
```

### 3. Setup Wizard Step Pattern (Frontend)
```tsx
// FROM: /opt/local-ai-packaged/management-ui/frontend/src/components/setup/EnvironmentStep.tsx:1-63
import React from 'react';
import { Card } from '../common/Card';
import { Home, Globe } from 'lucide-react';

interface EnvironmentStepProps {
  value: string;
  onChange: (value: string) => void;
}

export const EnvironmentStep: React.FC<EnvironmentStepProps> = ({ value, onChange }) => {
  return (
    <div>
      <h3 className="text-lg font-semibold text-white mb-2">Select Environment</h3>
      <p className="text-gray-400 mb-6">
        Choose how services will be accessible.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Card components with selection state */}
      </div>
    </div>
  );
};
```

### 4. Setup Schema Pattern (Backend)
```python
# FROM: /opt/local-ai-packaged/management-ui/backend/app/schemas/setup.py:29-34
class SetupConfigRequest(BaseModel):
    profile: Profile = Profile.CPU
    environment: Environment = Environment.PRIVATE
    enabled_services: List[str] = []
    secrets: Dict[str, str] = {}
    hostnames: Dict[str, str] = {}  # For public environment
```

### 5. Docker Compose Volume Override Pattern
```yaml
# FROM: /opt/local-ai-packaged/docker-compose.override.private.yml (inferred pattern)
# Override files extend base services
services:
  n8n:
    ports:
      - "127.0.0.1:5678:5678/tcp"
```

### 6. Stack Config Model Pattern
```python
# FROM: /opt/local-ai-packaged/management-ui/backend/app/models/stack_config.py:1-31
class StackConfig(Base):
    """Stores the user's stack configuration"""
    __tablename__ = "stack_config"

    id = Column(Integer, primary_key=True, index=True)
    profile = Column(String(20), nullable=False, default="cpu")
    environment = Column(String(20), nullable=False, default="private")
    enabled_services_json = Column(Text, nullable=False, default="[]")
    setup_completed = Column(Boolean, default=False)
```

### 7. Preflight Check Pattern
```python
# FROM: /opt/local-ai-packaged/management-ui/backend/app/services/setup_service.py:121-191
def preflight_check(self) -> dict:
    """Check environment state before setup."""
    issues = []
    warnings = []
    can_proceed = True

    # Check various conditions
    if some_condition:
        issues.append({
            "type": "issue_type",
            "message": "Human readable message",
            "fix": "fix_action_name"
        })
        can_proceed = False

    return {
        "can_proceed": can_proceed,
        "issues": issues,
        "warnings": warnings
    }
```

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `.env.example` | UPDATE | Add storage mode and path environment variables |
| `management-ui/backend/app/core/env_manager.py` | UPDATE | Add storage path validation schema |
| `management-ui/backend/app/schemas/setup.py` | UPDATE | Add storage configuration to setup schema |
| `management-ui/backend/app/models/stack_config.py` | UPDATE | Add storage_mode and storage_paths fields |
| `management-ui/backend/app/services/setup_service.py` | UPDATE | Add path validation, creation, and migration logic |
| `management-ui/backend/app/api/routes/setup.py` | UPDATE | Add storage endpoints (validate-path, migrate-volume) |
| `management-ui/frontend/src/components/setup/StorageStep.tsx` | CREATE | New wizard step for storage configuration |
| `management-ui/frontend/src/components/setup/SetupWizard.tsx` | UPDATE | Add StorageStep to wizard flow |
| `docker-compose.override.storage.yml` | CREATE | Override file for bind mount volumes |
| `management-ui/backend/app/core/docker_client.py` | UPDATE | Add methods for volume inspection and data copy |
| `scripts/migrate-volumes.py` | CREATE | Standalone migration script for CLI usage |

## NOT Building

- Volume backup/restore UI (out of scope for this feature - users use standard tools)
- Per-container storage path configuration (use single base path with subdirectories)
- Support for network-attached storage configuration (NFS, SMB mounts - user responsibility)
- Automatic permissions fixing without user confirmation (security risk)
- Cloud storage integration (S3, GCS - completely different feature)
- Hot migration while containers are running (requires stopping services)

## Tasks

### Task 1: UPDATE .env.example - Add Storage Configuration Variables

**Why**: Users need environment variables to configure storage mode and base path. These variables control whether the stack uses Docker volumes or bind mounts.

**Mirror**: `.env.example:85-111` (optional config section pattern)

**Do**:
Add the following section after the existing optional sections in `.env.example`:

```
############
# Optional Storage Configuration
# By default, data is stored in Docker named volumes.
# To use local filesystem paths instead (for easier backups), enable bind mounts.
############

# Storage mode: "volumes" (default) or "bind"
# STORAGE_MODE=volumes

# Base path for bind mount storage (only used when STORAGE_MODE=bind)
# This directory must exist and be writable by Docker containers
# Subdirectories will be created for each service (n8n, ollama, qdrant, etc.)
# STORAGE_BASE_PATH=/opt/local-ai-data

# Individual service storage paths (optional overrides)
# Uncomment to use custom paths for specific services
# N8N_DATA_PATH=${STORAGE_BASE_PATH}/n8n
# OLLAMA_DATA_PATH=${STORAGE_BASE_PATH}/ollama
# QDRANT_DATA_PATH=${STORAGE_BASE_PATH}/qdrant
# OPENWEBUI_DATA_PATH=${STORAGE_BASE_PATH}/open-webui
# FLOWISE_DATA_PATH=${STORAGE_BASE_PATH}/flowise
# NEO4J_DATA_PATH=${STORAGE_BASE_PATH}/neo4j
# LANGFUSE_POSTGRES_DATA_PATH=${STORAGE_BASE_PATH}/langfuse/postgres
# LANGFUSE_CLICKHOUSE_DATA_PATH=${STORAGE_BASE_PATH}/langfuse/clickhouse
# LANGFUSE_MINIO_DATA_PATH=${STORAGE_BASE_PATH}/langfuse/minio
# CADDY_DATA_PATH=${STORAGE_BASE_PATH}/caddy/data
# CADDY_CONFIG_PATH=${STORAGE_BASE_PATH}/caddy/config
# REDIS_DATA_PATH=${STORAGE_BASE_PATH}/redis
```

**Don't**:
- Add required validation for these fields (they're optional)
- Change existing environment variable names

**Verify**: `grep -n "STORAGE_MODE" /opt/local-ai-packaged/.env.example`


### Task 2: UPDATE env_manager.py - Add Storage Path Validation Schema

**Why**: The EnvManager needs schema entries for the new storage variables to validate paths and provide UI hints.

**Mirror**: `management-ui/backend/app/core/env_manager.py:8-90`

**Do**:
Add new entries to `ENV_SCHEMA` after the existing entries:

```python
# Storage Configuration
"STORAGE_MODE": {
    "category": "storage",
    "is_secret": False,
    "is_required": False,
    "description": "Storage mode: 'volumes' (Docker) or 'bind' (local paths)",
    "validation_regex": r"^(volumes|bind)$"
},
"STORAGE_BASE_PATH": {
    "category": "storage",
    "is_secret": False,
    "is_required": False,
    "description": "Base path for local storage (when STORAGE_MODE=bind)",
    "validation_regex": r"^/[a-zA-Z0-9/_-]+$"
},
```

Add a helper function at the end of the file:

```python
def validate_storage_path(path: str) -> Dict[str, Any]:
    """Validate a storage path for bind mount usage."""
    from pathlib import Path
    result = {
        "valid": False,
        "exists": False,
        "writable": False,
        "space_gb": 0,
        "errors": []
    }

    p = Path(path)

    # Check if path is absolute
    if not p.is_absolute():
        result["errors"].append("Path must be absolute (start with /)")
        return result

    # Check if path exists
    if p.exists():
        result["exists"] = True
        if not p.is_dir():
            result["errors"].append("Path exists but is not a directory")
            return result

    # Check parent directory for creation
    parent = p.parent
    if not parent.exists():
        result["errors"].append(f"Parent directory {parent} does not exist")
        return result

    # Check writability
    import os
    test_path = p if p.exists() else parent
    if os.access(test_path, os.W_OK):
        result["writable"] = True
    else:
        result["errors"].append("Directory is not writable")

    # Get available space
    import shutil
    try:
        usage = shutil.disk_usage(test_path)
        result["space_gb"] = round(usage.free / (1024**3), 1)
    except Exception:
        pass

    result["valid"] = len(result["errors"]) == 0
    return result
```

**Don't**:
- Make storage paths required fields
- Validate paths as secrets (they're not sensitive)

**Verify**: `python -c "from management_ui.backend.app.core.env_manager import validate_storage_path; print(validate_storage_path('/tmp'))"`


### Task 3: UPDATE setup.py schemas - Add Storage Configuration Types

**Why**: The setup request/response schemas need to include storage configuration options.

**Mirror**: `management-ui/backend/app/schemas/setup.py:6-34`

**Do**:
Add new enum and update SetupConfigRequest:

```python
class StorageMode(str, Enum):
    VOLUMES = "volumes"
    BIND = "bind"


class StorageConfig(BaseModel):
    mode: StorageMode = StorageMode.VOLUMES
    base_path: Optional[str] = None  # Only used when mode is BIND
    service_paths: Dict[str, str] = {}  # Optional per-service overrides


# Update SetupConfigRequest to add:
class SetupConfigRequest(BaseModel):
    profile: Profile = Profile.CPU
    environment: Environment = Environment.PRIVATE
    enabled_services: List[str] = []
    secrets: Dict[str, str] = {}
    hostnames: Dict[str, str] = {}
    storage: StorageConfig = StorageConfig()  # NEW


# Add new response model:
class StoragePathValidation(BaseModel):
    path: str
    valid: bool
    exists: bool
    writable: bool
    space_gb: float
    errors: List[str]
    warnings: List[str]


class VolumeMigrationStatus(BaseModel):
    volume_name: str
    service: str
    status: str  # pending, in_progress, completed, failed
    size_mb: float
    progress_percent: int
    error: Optional[str] = None
```

**Don't**:
- Make storage configuration required
- Remove existing fields from SetupConfigRequest

**Verify**: `python -c "from management_ui.backend.app.schemas.setup import StorageMode; print(StorageMode.BIND)"`


### Task 4: UPDATE stack_config.py - Add Storage Fields to Model

**Why**: The database model needs to persist the user's storage configuration choice.

**Mirror**: `management-ui/backend/app/models/stack_config.py:1-31`

**Do**:
Add new columns to StackConfig model:

```python
class StackConfig(Base):
    """Stores the user's stack configuration (enabled services, profile, etc.)"""
    __tablename__ = "stack_config"

    id = Column(Integer, primary_key=True, index=True)
    profile = Column(String(20), nullable=False, default="cpu")
    environment = Column(String(20), nullable=False, default="private")
    enabled_services_json = Column(Text, nullable=False, default="[]")
    setup_completed = Column(Boolean, default=False)
    # NEW: Storage configuration
    storage_mode = Column(String(10), nullable=False, default="volumes")
    storage_base_path = Column(String(255), nullable=True)
    storage_paths_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    @property
    def storage_paths(self) -> dict:
        """Get storage paths as a dict."""
        try:
            return json.loads(self.storage_paths_json)
        except (json.JSONDecodeError, TypeError):
            return {}

    @storage_paths.setter
    def storage_paths(self, value: dict):
        """Set storage paths from a dict."""
        self.storage_paths_json = json.dumps(value)
```

**Don't**:
- Create a migration file (SQLite auto-handles new columns)
- Remove existing columns

**Verify**: Check model loads without error


### Task 5: CREATE docker-compose.override.storage.yml - Bind Mount Overrides

**Why**: This override file replaces Docker named volumes with bind mount paths using environment variable substitution.

**Mirror**: `docker-compose.yml` volume definitions (lines 4-16, 43-44, 81-82, etc.)

**Do**:
Create `/opt/local-ai-packaged/docker-compose.override.storage.yml`:

```yaml
# Docker Compose override for bind mount storage
# Generated when STORAGE_MODE=bind
# Replaces named volumes with local filesystem paths

services:
  n8n:
    volumes:
      - ${N8N_DATA_PATH:-${STORAGE_BASE_PATH}/n8n}:/home/node/.n8n
      - ./n8n/backup:/backup
      - ./shared:/data/shared

  open-webui:
    volumes:
      - ${OPENWEBUI_DATA_PATH:-${STORAGE_BASE_PATH}/open-webui}:/app/backend/data

  flowise:
    volumes:
      - ${FLOWISE_DATA_PATH:-${STORAGE_BASE_PATH}/flowise}:/root/.flowise

  qdrant:
    volumes:
      - ${QDRANT_DATA_PATH:-${STORAGE_BASE_PATH}/qdrant}:/qdrant/storage

  caddy:
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - ./caddy-addon:/etc/caddy/addons:ro
      - ${CADDY_DATA_PATH:-${STORAGE_BASE_PATH}/caddy/data}:/data:rw
      - ${CADDY_CONFIG_PATH:-${STORAGE_BASE_PATH}/caddy/config}:/config:rw

  clickhouse:
    volumes:
      - ${LANGFUSE_CLICKHOUSE_DATA_PATH:-${STORAGE_BASE_PATH}/langfuse/clickhouse/data}:/var/lib/clickhouse
      - ${LANGFUSE_CLICKHOUSE_LOGS_PATH:-${STORAGE_BASE_PATH}/langfuse/clickhouse/logs}:/var/log/clickhouse-server

  minio:
    volumes:
      - ${LANGFUSE_MINIO_DATA_PATH:-${STORAGE_BASE_PATH}/langfuse/minio}:/data

  postgres:
    volumes:
      - ${LANGFUSE_POSTGRES_DATA_PATH:-${STORAGE_BASE_PATH}/langfuse/postgres}:/var/lib/postgresql/data

  redis:
    volumes:
      - ${REDIS_DATA_PATH:-${STORAGE_BASE_PATH}/redis}:/data

# Note: Ollama storage path handled dynamically based on profile
# The x-ollama anchor in main compose uses ollama_storage volume
# This override applies when STORAGE_MODE=bind
```

**Don't**:
- Override the main volumes: section (keep it for when volumes mode is used)
- Include services that use relative path bind mounts (like neo4j which uses ./neo4j/*)

**Verify**: `docker compose -f docker-compose.yml -f docker-compose.override.storage.yml config`


### Task 6: UPDATE docker_client.py - Add Volume Inspection and Migration Methods

**Why**: Need to inspect existing Docker volumes and copy data to bind mount paths for migration.

**Mirror**: `management-ui/backend/app/core/docker_client.py:1-143`

**Do**:
Add new methods to DockerClient class:

```python
def list_project_volumes(self) -> List[Dict]:
    """List all Docker volumes used by this project."""
    volumes = self.client.volumes.list(filters={"name": f"{self.project}_"})
    result = []
    for vol in volumes:
        # Get volume info
        attrs = vol.attrs
        result.append({
            "name": vol.name,
            "driver": attrs.get("Driver", "local"),
            "mountpoint": attrs.get("Mountpoint", ""),
            "created": attrs.get("CreatedAt", ""),
            "labels": attrs.get("Labels", {}),
        })
    return result

def get_volume_size(self, volume_name: str) -> int:
    """Get size of a Docker volume in bytes."""
    try:
        result = subprocess.run(
            ["docker", "system", "df", "-v", "--format", "{{json .}}"],
            capture_output=True, text=True
        )
        # Parse JSON output to find volume size
        # Returns approximate size in bytes
        return 0  # Placeholder
    except Exception:
        return 0

def copy_volume_to_path(self, volume_name: str, target_path: str) -> Dict:
    """Copy data from a Docker volume to a local path using rsync."""
    import os
    from pathlib import Path

    target = Path(target_path)
    if not target.exists():
        target.mkdir(parents=True, exist_ok=True)

    # Use a temporary container to mount volume and copy
    try:
        result = subprocess.run([
            "docker", "run", "--rm",
            "-v", f"{volume_name}:/source:ro",
            "-v", f"{target_path}:/target",
            "alpine", "sh", "-c",
            "apk add --no-cache rsync && rsync -av /source/ /target/"
        ], capture_output=True, text=True, timeout=3600)

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Migration timed out after 1 hour"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
```

**Don't**:
- Modify existing methods
- Use docker-py for volume copy (subprocess with rsync container is more reliable)

**Verify**: Unit test the methods with mock Docker client


### Task 7: UPDATE setup_service.py - Add Storage Path Validation and Directory Creation

**Why**: Setup service needs to validate storage paths, create directories, and handle migration.

**Mirror**: `management-ui/backend/app/services/setup_service.py:282-324` (prepare_env_file pattern)

**Do**:
Add new methods to SetupService class:

```python
def validate_storage_path(self, path: str) -> Dict:
    """Validate a storage path for bind mount usage."""
    from ..core.env_manager import validate_storage_path
    result = validate_storage_path(path)

    # Add warnings
    warnings = []
    if result["space_gb"] < 20:
        warnings.append(f"Low disk space: {result['space_gb']}GB available. Recommend 50GB+")

    result["warnings"] = warnings
    return result

def prepare_storage_directories(self, base_path: str, services: List[str]) -> SetupStepResult:
    """Create storage directories with correct permissions."""
    from pathlib import Path
    import os

    base = Path(base_path)

    # Service -> subdirectory mapping with recommended ownership
    service_dirs = {
        "n8n": ("n8n", 1000, 1000),  # node user
        "ollama": ("ollama", 0, 0),  # root
        "open-webui": ("open-webui", 0, 0),
        "flowise": ("flowise", 0, 0),
        "qdrant": ("qdrant", 1000, 1000),
        "neo4j": ("neo4j", 7474, 7474),
        "clickhouse": ("langfuse/clickhouse", 101, 101),
        "minio": ("langfuse/minio", 1000, 1000),
        "postgres": ("langfuse/postgres", 999, 999),
        "redis": ("redis", 999, 1000),
        "caddy": ("caddy", 0, 0),
    }

    created = []
    errors = []

    try:
        # Create base directory if needed
        if not base.exists():
            base.mkdir(parents=True, mode=0o755)
            created.append(str(base))

        # Create service subdirectories
        for svc, (subdir, uid, gid) in service_dirs.items():
            if svc in services or any(svc in s for s in services):
                svc_path = base / subdir
                if not svc_path.exists():
                    svc_path.mkdir(parents=True, mode=0o755)
                    created.append(str(svc_path))
                    # Note: chown requires root - document this

        return SetupStepResult(
            step="prepare_storage",
            status="completed",
            message=f"Created {len(created)} directories"
        )
    except Exception as e:
        return SetupStepResult(
            step="prepare_storage",
            status="failed",
            error=str(e)
        )

async def migrate_volumes_to_paths(
    self,
    volume_mappings: Dict[str, str]
) -> List[Dict]:
    """Migrate data from Docker volumes to local paths."""
    results = []

    for volume_name, target_path in volume_mappings.items():
        result = self.docker_client.copy_volume_to_path(volume_name, target_path)
        results.append({
            "volume": volume_name,
            "target": target_path,
            **result
        })

    return results
```

Update `run_full_setup` to handle storage configuration:

```python
async def run_full_setup(self, config: SetupConfigRequest) -> SetupProgressResponse:
    """Run the complete setup process."""
    steps: List[SetupStepResult] = []

    # ... existing steps ...

    # NEW: Step for storage preparation (after prepare_env, before start_stack)
    if config.storage.mode == StorageMode.BIND:
        result = self.prepare_storage_directories(
            config.storage.base_path,
            config.enabled_services
        )
        steps.append(result)
        if result.status == "failed":
            return SetupProgressResponse(
                status="failed",
                current_step="prepare_storage",
                steps=steps,
                error=result.error
            )

    # ... continue with start_stack ...
```

**Don't**:
- Automatically chown directories (requires root, document instead)
- Delete existing data during migration

**Verify**: Test path validation with various inputs


### Task 8: UPDATE setup.py routes - Add Storage API Endpoints

**Why**: Frontend needs API endpoints to validate paths and initiate migration.

**Mirror**: `management-ui/backend/app/api/routes/setup.py:63-80` (preflight pattern)

**Do**:
Add new endpoints:

```python
@router.post("/validate-storage-path", response_model=StoragePathValidation)
async def validate_storage_path(
    path: str = Body(..., embed=True),
    setup_service: SetupService = Depends(get_setup_service),
    _: dict = Depends(get_current_user)
):
    """Validate a storage path for bind mount usage."""
    result = setup_service.validate_storage_path(path)
    return StoragePathValidation(
        path=path,
        valid=result["valid"],
        exists=result["exists"],
        writable=result["writable"],
        space_gb=result["space_gb"],
        errors=result.get("errors", []),
        warnings=result.get("warnings", [])
    )


@router.get("/volumes")
async def list_volumes(
    setup_service: SetupService = Depends(get_setup_service),
    _: dict = Depends(get_current_user)
):
    """List existing Docker volumes that can be migrated."""
    volumes = setup_service.docker_client.list_project_volumes()
    return {"volumes": volumes}


@router.post("/migrate-volume")
async def migrate_volume(
    volume_name: str = Body(...),
    target_path: str = Body(...),
    setup_service: SetupService = Depends(get_setup_service),
    _: dict = Depends(get_current_user)
):
    """Migrate a single volume to a local path."""
    # Validate target path first
    validation = setup_service.validate_storage_path(target_path)
    if not validation["valid"]:
        return {"success": False, "errors": validation["errors"]}

    result = setup_service.docker_client.copy_volume_to_path(volume_name, target_path)
    return result
```

**Don't**:
- Allow migration without authentication
- Skip path validation before migration

**Verify**: `curl -X POST /api/setup/validate-storage-path -d '{"path": "/tmp/test"}'`


### Task 9: CREATE StorageStep.tsx - New Wizard Step Component

**Why**: Users need a UI step to configure storage mode and validate paths.

**Mirror**: `management-ui/frontend/src/components/setup/EnvironmentStep.tsx`

**Do**:
Create `/opt/local-ai-packaged/management-ui/frontend/src/components/setup/StorageStep.tsx`:

```tsx
import React, { useState, useEffect } from 'react';
import { Card } from '../common/Card';
import { Input } from '../common/Input';
import { Button } from '../common/Button';
import { HardDrive, Database, CheckCircle, XCircle, AlertTriangle, Loader2 } from 'lucide-react';
import { apiClient } from '../../api/client';

interface StorageStepProps {
  value: {
    mode: string;
    base_path: string;
  };
  onChange: (value: { mode: string; base_path: string }) => void;
}

interface PathValidation {
  valid: boolean;
  exists: boolean;
  writable: boolean;
  space_gb: number;
  errors: string[];
  warnings: string[];
}

export const StorageStep: React.FC<StorageStepProps> = ({ value, onChange }) => {
  const [validation, setValidation] = useState<PathValidation | null>(null);
  const [isValidating, setIsValidating] = useState(false);

  const validatePath = async (path: string) => {
    if (!path || value.mode !== 'bind') return;

    setIsValidating(true);
    try {
      const response = await apiClient.post<PathValidation>('/setup/validate-storage-path', { path });
      setValidation(response.data);
    } catch (e) {
      setValidation({
        valid: false,
        exists: false,
        writable: false,
        space_gb: 0,
        errors: ['Failed to validate path'],
        warnings: []
      });
    } finally {
      setIsValidating(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      if (value.base_path && value.mode === 'bind') {
        validatePath(value.base_path);
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [value.base_path, value.mode]);

  return (
    <div>
      <h3 className="text-lg font-semibold text-white mb-2">Storage Configuration</h3>
      <p className="text-gray-400 mb-6">
        Choose how service data should be stored.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <Card
          className={`cursor-pointer transition-all ${
            value.mode === 'volumes' ? 'ring-2 ring-blue-500 border-blue-500' : 'hover:border-gray-500'
          }`}
          onClick={() => onChange({ ...value, mode: 'volumes' })}
        >
          <div className="flex items-start gap-3">
            <Database className="w-6 h-6 text-blue-400 flex-shrink-0" />
            <div>
              <h4 className="font-medium text-white">Docker Volumes (Default)</h4>
              <p className="text-sm text-gray-400 mt-1">
                Data stored in Docker-managed volumes. Portable and isolated.
                Best for most users.
              </p>
              <p className="text-xs text-gray-500 mt-2">
                Backup: docker volume commands
              </p>
            </div>
          </div>
        </Card>

        <Card
          className={`cursor-pointer transition-all ${
            value.mode === 'bind' ? 'ring-2 ring-blue-500 border-blue-500' : 'hover:border-gray-500'
          }`}
          onClick={() => onChange({ ...value, mode: 'bind' })}
        >
          <div className="flex items-start gap-3">
            <HardDrive className="w-6 h-6 text-green-400 flex-shrink-0" />
            <div>
              <h4 className="font-medium text-white">Local Filesystem</h4>
              <p className="text-sm text-gray-400 mt-1">
                Data stored in local directories. Easier to access and backup
                with standard tools (rsync, Borg, etc.).
              </p>
              <p className="text-xs text-gray-500 mt-2">
                Backup: rsync, cp, any backup tool
              </p>
            </div>
          </div>
        </Card>
      </div>

      {value.mode === 'bind' && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Base Storage Path
            </label>
            <div className="flex gap-2">
              <Input
                value={value.base_path}
                onChange={(e) => onChange({ ...value, base_path: e.target.value })}
                placeholder="/opt/local-ai-data"
                className="flex-1"
              />
              <Button
                variant="secondary"
                onClick={() => validatePath(value.base_path)}
                disabled={isValidating}
              >
                {isValidating ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Validate'}
              </Button>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Subdirectories will be created for each service (n8n, ollama, etc.)
            </p>
          </div>

          {validation && (
            <div className={`p-4 rounded-lg border ${
              validation.valid
                ? 'bg-green-900/20 border-green-700'
                : 'bg-red-900/20 border-red-700'
            }`}>
              <div className="flex items-center gap-2 mb-2">
                {validation.valid ? (
                  <CheckCircle className="w-5 h-5 text-green-400" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-400" />
                )}
                <span className={validation.valid ? 'text-green-400' : 'text-red-400'}>
                  {validation.valid ? 'Path is valid' : 'Path validation failed'}
                </span>
              </div>

              {validation.valid && (
                <div className="text-sm text-gray-400 space-y-1">
                  <p>Available space: {validation.space_gb} GB</p>
                  <p>Directory exists: {validation.exists ? 'Yes' : 'Will be created'}</p>
                </div>
              )}

              {validation.errors.length > 0 && (
                <ul className="text-sm text-red-400 mt-2 space-y-1">
                  {validation.errors.map((err, i) => (
                    <li key={i}>{err}</li>
                  ))}
                </ul>
              )}

              {validation.warnings.length > 0 && (
                <div className="mt-2">
                  {validation.warnings.map((warn, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm text-yellow-400">
                      <AlertTriangle className="w-4 h-4" />
                      <span>{warn}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="bg-gray-800 p-4 rounded-lg">
            <h4 className="text-sm font-medium text-white mb-2">Permission Requirements</h4>
            <p className="text-xs text-gray-400">
              Some services run as specific users. After setup, you may need to adjust ownership:
            </p>
            <pre className="mt-2 text-xs text-gray-500 bg-gray-900 p-2 rounded overflow-x-auto">
{`# ClickHouse (UID 101)
sudo chown -R 101:101 ${value.base_path || '/opt/local-ai-data'}/langfuse/clickhouse

# PostgreSQL (UID 999)
sudo chown -R 999:999 ${value.base_path || '/opt/local-ai-data'}/langfuse/postgres`}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};
```

**Don't**:
- Auto-submit on path change (use debounce)
- Make the component too complex - keep it focused on storage config

**Verify**: Component renders without errors in dev mode


### Task 10: UPDATE SetupWizard.tsx - Integrate StorageStep

**Why**: The StorageStep needs to be added to the wizard flow.

**Mirror**: `management-ui/frontend/src/components/setup/SetupWizard.tsx:14-17, 103-141`

**Do**:
Update SetupWizard.tsx:

1. Add import:
```tsx
import { StorageStep } from './StorageStep';
```

2. Update STEPS and STEP_LABELS:
```tsx
const STEPS = ['preflight', 'profile', 'services', 'environment', 'storage', 'secrets', 'confirm'] as const;
const STEP_LABELS = ['Check', 'Profile', 'Services', 'Environment', 'Storage', 'Secrets', 'Confirm'];
```

3. Update SetupConfig interface:
```tsx
interface SetupConfig {
  profile: string;
  environment: string;
  secrets: Record<string, string>;
  enabled_services: string[];
  storage: {
    mode: string;
    base_path: string;
  };
}
```

4. Update initial state:
```tsx
const [config, setConfig] = useState<SetupConfig>({
  profile: 'cpu',
  environment: 'private',
  secrets: {},
  enabled_services: [],
  storage: {
    mode: 'volumes',
    base_path: '/opt/local-ai-data',
  },
});
```

5. Update canProceed():
```tsx
case 'storage':
  // If bind mode, path must be provided
  if (config.storage.mode === 'bind' && !config.storage.base_path) {
    return false;
  }
  return true;
```

6. Add case to renderStep():
```tsx
case 'storage':
  return (
    <StorageStep
      value={config.storage}
      onChange={(storage) => setConfig({ ...config, storage })}
    />
  );
```

**Don't**:
- Remove existing steps
- Change the order of other steps

**Verify**: Wizard displays all 7 steps correctly


### Task 11: UPDATE docker_client.py - Add Storage Override to Compose Command

**Why**: When storage mode is "bind", compose commands need to include the storage override file.

**Mirror**: `management-ui/backend/app/core/docker_client.py:99-118`

**Do**:
Update `_build_compose_command` method:

```python
def _build_compose_command(
    self,
    profile: Optional[str] = None,
    environment: str = "private",
    storage_mode: str = "volumes"  # NEW parameter
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

    # NEW: Add storage override if using bind mounts
    if storage_mode == "bind":
        storage_override = Path(self.base_path) / "docker-compose.override.storage.yml"
        if storage_override.exists():
            cmd.extend(["-f", "docker-compose.override.storage.yml"])

    return cmd
```

Update `compose_up` and `compose_down` to accept storage_mode parameter and pass it through.

**Don't**:
- Break existing functionality when storage_mode is not specified
- Apply storage override when mode is "volumes"

**Verify**: `docker compose -f docker-compose.yml -f docker-compose.override.storage.yml config` works


### Task 12: CREATE scripts/migrate-volumes.py - Standalone Migration Script

**Why**: Users may want to migrate volumes outside the web UI, especially for large datasets.

**Mirror**: `start_services.py` (standalone script pattern)

**Do**:
Create `/opt/local-ai-packaged/scripts/migrate-volumes.py`:

```python
#!/usr/bin/env python3
"""
migrate-volumes.py

Migrate data from Docker named volumes to local filesystem paths.
This script is useful for large datasets where web UI migration might timeout.

Usage:
    python migrate-volumes.py --target /opt/local-ai-data [--dry-run]
    python migrate-volumes.py --volume localai_n8n_storage --target /opt/local-ai-data/n8n
"""

import argparse
import subprocess
import sys
from pathlib import Path


# Volume name -> subdirectory mapping
VOLUME_MAP = {
    "localai_n8n_storage": "n8n",
    "localai_ollama_storage": "ollama",
    "localai_qdrant_storage": "qdrant",
    "localai_open-webui": "open-webui",
    "localai_flowise": "flowise",
    "localai_caddy-data": "caddy/data",
    "localai_caddy-config": "caddy/config",
    "localai_valkey-data": "redis",
    "localai_langfuse_postgres_data": "langfuse/postgres",
    "localai_langfuse_clickhouse_data": "langfuse/clickhouse/data",
    "localai_langfuse_clickhouse_logs": "langfuse/clickhouse/logs",
    "localai_langfuse_minio_data": "langfuse/minio",
}


def get_existing_volumes():
    """Get list of existing Docker volumes for this project."""
    result = subprocess.run(
        ["docker", "volume", "ls", "-q", "--filter", "name=localai_"],
        capture_output=True, text=True
    )
    return [v for v in result.stdout.strip().split("\n") if v]


def get_volume_size(volume_name: str) -> str:
    """Get human-readable size of a volume."""
    result = subprocess.run(
        ["docker", "run", "--rm", "-v", f"{volume_name}:/vol", "alpine",
         "sh", "-c", "du -sh /vol 2>/dev/null || echo 'unknown'"],
        capture_output=True, text=True
    )
    return result.stdout.strip().split()[0] if result.returncode == 0 else "unknown"


def migrate_volume(volume_name: str, target_path: str, dry_run: bool = False):
    """Migrate a single volume to a local path."""
    target = Path(target_path)

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Migrating {volume_name} -> {target_path}")

    # Get volume size
    size = get_volume_size(volume_name)
    print(f"  Volume size: {size}")

    if dry_run:
        print(f"  Would create directory: {target_path}")
        print(f"  Would copy data using rsync")
        return True

    # Create target directory
    target.mkdir(parents=True, exist_ok=True)

    # Run rsync in container
    print(f"  Copying data...")
    result = subprocess.run([
        "docker", "run", "--rm",
        "-v", f"{volume_name}:/source:ro",
        "-v", f"{target_path}:/target",
        "alpine", "sh", "-c",
        "apk add --no-cache rsync >/dev/null 2>&1 && rsync -av /source/ /target/"
    ], capture_output=True, text=True)

    if result.returncode == 0:
        print(f"  Success!")
        return True
    else:
        print(f"  Failed: {result.stderr}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Migrate Docker volumes to local filesystem paths"
    )
    parser.add_argument(
        "--target", "-t",
        help="Base target directory for all volumes (e.g., /opt/local-ai-data)"
    )
    parser.add_argument(
        "--volume", "-v",
        help="Migrate a specific volume only"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        dest="list_volumes",
        help="List existing volumes and exit"
    )

    args = parser.parse_args()

    # Get existing volumes
    volumes = get_existing_volumes()

    if args.list_volumes:
        print("Existing volumes:")
        for vol in volumes:
            size = get_volume_size(vol)
            subdir = VOLUME_MAP.get(vol, "unknown")
            print(f"  {vol} ({size}) -> {subdir}/")
        return 0

    if not args.target:
        parser.error("--target is required for migration")

    base_target = Path(args.target)

    # Check if containers are running
    result = subprocess.run(
        ["docker", "compose", "-p", "localai", "ps", "-q"],
        capture_output=True, text=True
    )
    if result.stdout.strip():
        print("WARNING: Containers are running. Stop them first for safe migration:")
        print("  docker compose -p localai down")
        if not args.dry_run:
            response = input("Continue anyway? [y/N] ")
            if response.lower() != 'y':
                return 1

    # Migrate volumes
    if args.volume:
        # Single volume
        if args.volume not in volumes:
            print(f"Error: Volume {args.volume} not found")
            return 1
        subdir = VOLUME_MAP.get(args.volume, args.volume.replace("localai_", ""))
        target = base_target / subdir
        success = migrate_volume(args.volume, str(target), args.dry_run)
        return 0 if success else 1
    else:
        # All volumes
        success_count = 0
        for vol in volumes:
            if vol in VOLUME_MAP:
                target = base_target / VOLUME_MAP[vol]
                if migrate_volume(vol, str(target), args.dry_run):
                    success_count += 1

        print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Migrated {success_count}/{len(volumes)} volumes")
        return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Don't**:
- Delete original volumes after migration (user should do this manually)
- Run without warning when containers are active

**Verify**: `python scripts/migrate-volumes.py --list`


### Task 13: UPDATE setup_service.py start_stack - Pass Storage Mode

**Why**: The start_stack method needs to use the storage override when storage mode is "bind".

**Mirror**: `management-ui/backend/app/services/setup_service.py:354-411`

**Do**:
Update `start_stack` method signature and implementation:

```python
async def start_stack(
    self,
    profile: str,
    environment: str,
    enabled_services: Optional[List[str]] = None,
    storage_mode: str = "volumes"  # NEW parameter
) -> SetupStepResult:
    """Start the full stack."""
    try:
        # Stop existing containers first
        self.docker_client.compose_down(profile=profile)

        # ... existing Supabase start code ...

        # Start local AI services with storage mode
        result = self.docker_client.compose_up(
            services=enabled_services,
            profile=profile,
            environment=environment,
            storage_mode=storage_mode  # Pass through
        )

        # ... rest of method ...
```

Update `run_full_setup` to pass storage mode:

```python
result = await self.start_stack(
    profile=config.profile.value,
    environment=config.environment.value,
    enabled_services=config.enabled_services if config.enabled_services else None,
    storage_mode=config.storage.mode.value  # NEW
)
```

**Don't**:
- Change storage mode during runtime (requires restart)
- Apply storage override to Supabase services (they have their own volume management)

**Verify**: Stack starts correctly with both storage modes


### Task 14: UPDATE complete_setup route - Save Storage Configuration

**Why**: The storage configuration needs to be persisted to the database.

**Mirror**: `management-ui/backend/app/api/routes/setup.py:113-148`

**Do**:
Update the `complete_setup` endpoint:

```python
@router.post("/complete", response_model=SetupProgressResponse)
async def complete_setup(
    config: SetupConfigRequest,
    setup_service: SetupService = Depends(get_setup_service),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    """Run the complete setup process."""
    result = await setup_service.run_full_setup(config)

    # Save stack config to database on success
    if result.status == "completed":
        # ... existing validation code ...

        # Remove existing config if any
        db.query(StackConfig).delete()

        # Create new config with storage settings
        stack_config = StackConfig(
            profile=config.profile.value,
            environment=config.environment.value,
            setup_completed=True,
            storage_mode=config.storage.mode.value,  # NEW
            storage_base_path=config.storage.base_path if config.storage.mode == StorageMode.BIND else None  # NEW
        )
        stack_config.enabled_services = all_enabled
        db.add(stack_config)
        db.commit()

    return result
```

**Don't**:
- Store storage paths in .env for Supabase services (they manage their own volumes)

**Verify**: Database contains storage_mode after setup completion

## Validation Strategy

### Automated Checks
- [ ] `cd management-ui/backend && python -m pytest` - Backend unit tests pass
- [ ] `cd management-ui/frontend && npm run type-check` - TypeScript types valid
- [ ] `cd management-ui/frontend && npm run lint` - No lint errors
- [ ] `cd management-ui/frontend && npm run build` - Frontend builds successfully
- [ ] `docker compose -f docker-compose.yml -f docker-compose.override.storage.yml config` - Compose files valid

### New Tests to Write
| Test File | Test Case | What It Validates |
|-----------|-----------|-------------------|
| `test_env_manager.py` | `test_validate_storage_path_valid` | Path validation returns correct structure |
| `test_env_manager.py` | `test_validate_storage_path_not_absolute` | Rejects relative paths |
| `test_env_manager.py` | `test_validate_storage_path_not_writable` | Detects permission issues |
| `test_setup_service.py` | `test_prepare_storage_directories` | Creates correct directory structure |
| `test_docker_client.py` | `test_list_project_volumes` | Lists volumes with correct prefix |
| `test_docker_client.py` | `test_compose_command_with_storage` | Includes storage override file |

### Manual/E2E Validation

```bash
# 1. Test storage path validation API
curl -X POST http://localhost:9009/api/setup/validate-storage-path \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"path": "/opt/local-ai-data"}'

# 2. Test volume listing
curl http://localhost:9009/api/setup/volumes \
  -H "Authorization: Bearer $TOKEN"

# 3. Test migration script
python scripts/migrate-volumes.py --list
python scripts/migrate-volumes.py --target /tmp/test-migrate --dry-run

# 4. Full wizard flow test
# - Go through setup wizard
# - Select "Local Filesystem" storage
# - Enter path: /opt/local-ai-data
# - Validate path shows green checkmark
# - Complete setup
# - Verify services start with bind mounts:
docker inspect localai-n8n-1 | grep -A5 "Mounts"
```

### Edge Cases to Test
- [ ] Empty storage path when bind mode selected - should show error
- [ ] Non-existent parent directory - should fail validation
- [ ] Path with spaces - should work (quoted in compose)
- [ ] Path on different filesystem - should show available space correctly
- [ ] Migrating large volume (>10GB) - should complete without timeout
- [ ] Migration with containers running - should warn user
- [ ] Path without write permission - should fail validation
- [ ] Switching from bind back to volumes - should work (data stays in bind path)

### Regression Check
- [ ] Setup wizard still works with "Docker Volumes" selected (existing behavior)
- [ ] Existing stacks using volumes continue to work after code update
- [ ] All existing API endpoints still function correctly

## Risks

1. **Permission Issues**: Users may encounter permission errors if bind mount directories have wrong ownership. Mitigation: Provide clear documentation and permission fix commands in UI.

2. **Data Loss During Migration**: If migration fails midway, data could be in inconsistent state. Mitigation: Use rsync (atomic copy), don't delete source volumes, warn user to backup first.

3. **SELinux Compatibility**: On RHEL/Fedora systems, SELinux may block container access to bind mounts. Mitigation: Document need for `:z` suffix on mounts for SELinux systems.

4. **Large Dataset Migration Timeout**: Web UI has request timeouts that could fail for large datasets. Mitigation: Provide standalone migration script for CLI usage.

5. **Supabase Volume Compatibility**: Supabase has its own volume management in docker-compose.yml. Mitigation: Do not apply storage override to Supabase services, only to local-ai services.
