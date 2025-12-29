# Plan: Backup & Restore System

## Summary

Implement a comprehensive backup and restore system for the local-ai-packaged management UI that supports:
1. Docker volume backups using temporary containers to safely copy data
2. Service-specific backup strategies (pg_dump for PostgreSQL, file-level for others)
3. Multiple backup destinations (local filesystem and S3/MinIO already in the stack)
4. Scheduled backup jobs with configurable frequencies
5. One-click restore functionality with integrity verification
6. Extension of the existing BackupManager component for full volume backup support

The approach uses database-native backup tools for data consistency (pg_dump for PostgreSQL) and file-level backups for other volumes, storing backups either locally or to the existing MinIO service.

## External Research

### Documentation
- [Docker Docs - Volumes](https://docs.docker.com/engine/storage/volumes/) - Official volume management
- [Offen/docker-volume-backup](https://github.com/offen/docker-volume-backup) - S3-compatible backup tool
- [PostgreSQL pg_dump](https://simplebackups.com/blog/docker-postgres-backup-restore-guide-with-examples/) - Docker PostgreSQL backup
- [MinIO Python SDK](https://pypi.org/project/minio/) - S3-compatible storage SDK
- [boto3 S3 Uploading](https://boto3.amazonaws.com/v1/documentation/api/1.9.185/guide/s3-uploading-files.html) - AWS SDK for Python

### Gotchas & Best Practices
- **Database backups require pg_dump**: Generic volume backups risk file corruption for running databases
- **ext4 doesn't support COW**: File corruption possible if backing up running containers without stopping
- **Stop containers for file backups**: Or use application-specific dump tools for databases
- **Compression is critical**: Use gzip -9 for backups to save storage
- **Test restore regularly**: A backup is only as good as your ability to restore from it
- **MinIO requires path-style URLs**: Set `LANGFUSE_S3_EVENT_UPLOAD_FORCE_PATH_STYLE=true`
- **pg_dump with --no-owner**: Ensures portability across different PostgreSQL instances

## Patterns to Mirror

### Backend API Route Pattern
```python
# FROM: management-ui/backend/app/api/routes/config.py:95-102
# This is how backup list endpoints are structured:
@router.get("/backups", response_model=BackupListResponse)
async def list_backups(
    env_manager: EnvManager = Depends(get_env_manager),
    _: dict = Depends(get_current_user)
):
    """List available configuration backups."""
    backups = env_manager.list_backups()
    return BackupListResponse(backups=[BackupInfo(**b) for b in backups])
```

### Backend Schema Pattern
```python
# FROM: management-ui/backend/app/schemas/config.py:43-60
# This is how backup-related schemas are defined:
class BackupInfo(BaseModel):
    filename: str
    path: str
    created: str

class BackupListResponse(BaseModel):
    backups: List[BackupInfo]

class RestoreRequest(BaseModel):
    filename: str

class MessageResponse(BaseModel):
    message: str
    backup_path: Optional[str] = None
```

### Frontend API Client Pattern
```typescript
// FROM: management-ui/frontend/src/api/config.ts:37-44
// This is how backup API calls are structured:
async listBackups(): Promise<{ backups: BackupInfo[] }> {
  const response = await apiClient.get('/config/backups');
  return response.data;
},

async restoreBackup(filename: string): Promise<{ message: string }> {
  const response = await apiClient.post('/config/restore', { filename });
  return response.data;
},
```

### Frontend Component Pattern (BackupManager)
```typescript
// FROM: management-ui/frontend/src/components/config/BackupManager.tsx:6-17
// This is how backup manager components are structured:
interface BackupManagerProps {
  backups: BackupInfo[];
  onRestore: (filename: string) => void;
  onRefresh: () => void;
  isRestoring?: boolean;
}

export const BackupManager: React.FC<BackupManagerProps> = ({
  backups,
  onRestore,
  onRefresh,
  isRestoring = false,
}) => {
```

### Docker Client Pattern
```python
# FROM: management-ui/backend/app/core/docker_client.py:7-14
# This is how the Docker client is initialized:
class DockerClient:
    """Wrapper around docker-py with compose integration."""

    def __init__(self, project: str = "localai", base_path: str = None):
        self.client = docker.from_env()
        self.project = project
        self.base_path = base_path or os.environ.get("COMPOSE_BASE_PATH", ".")
```

### Zustand Store Pattern
```typescript
// FROM: management-ui/frontend/src/store/configStore.ts:164-171
// This is how backup state is managed:
fetchBackups: async () => {
  try {
    const response = await configApi.listBackups();
    set({ backups: response.backups });
  } catch (error: unknown) {
    console.error('Failed to fetch backups:', error);
  }
},
```

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `backend/app/core/backup_manager.py` | CREATE | Core backup logic for volumes, databases, and S3 uploads |
| `backend/app/core/backup_scheduler.py` | CREATE | Cron-like scheduler for automated backups |
| `backend/app/schemas/backup.py` | CREATE | Pydantic schemas for backup API |
| `backend/app/api/routes/backup.py` | CREATE | REST API endpoints for backup operations |
| `backend/app/api/routes/__init__.py` | UPDATE | Register backup router |
| `backend/app/api/deps.py` | UPDATE | Add backup manager dependency |
| `backend/app/config.py` | UPDATE | Add backup configuration settings |
| `backend/requirements.txt` | UPDATE | Add boto3 for S3 support |
| `frontend/src/types/backup.ts` | CREATE | TypeScript types for backup data |
| `frontend/src/api/backup.ts` | CREATE | API client for backup endpoints |
| `frontend/src/store/backupStore.ts` | CREATE | Zustand store for backup state |
| `frontend/src/components/backup/VolumeBackupManager.tsx` | CREATE | Main backup management component |
| `frontend/src/components/backup/BackupScheduleConfig.tsx` | CREATE | Schedule configuration UI |
| `frontend/src/components/backup/BackupDestinationConfig.tsx` | CREATE | Destination (local/S3) configuration |
| `frontend/src/components/backup/index.ts` | CREATE | Component barrel export |
| `frontend/src/pages/Backups.tsx` | CREATE | Dedicated backup management page |
| `frontend/src/App.tsx` | UPDATE | Add /backups route |
| `frontend/src/components/layout/Sidebar.tsx` | UPDATE | Add Backups nav item |

## NOT Building

- Real-time backup progress streaming (use polling instead for simplicity)
- Incremental/differential backups (full backups only in v1)
- Backup encryption (can be added later with GPG)
- External S3 providers (only MinIO in stack for v1)
- Point-in-time recovery for databases (beyond scope)
- Backup retention policies with automatic deletion (manual deletion in v1)
- Multi-volume atomic snapshots (backup one volume at a time)
- Remote backup destinations beyond S3 (SSH, WebDAV, etc.)

## Tasks

### Task 1: Add boto3 Dependency

**Why**: Required for S3/MinIO uploads. boto3 is the standard AWS SDK for Python.

**Mirror**: `backend/requirements.txt` format

**File**: `management-ui/backend/requirements.txt`

**Do**:
Add to the end of the file:
```
boto3>=1.34.0
```

**Don't**:
- Don't add minio SDK (boto3 is more versatile and handles MinIO well)

**Verify**: `cd /opt/local-ai-packaged/management-ui/backend && pip install boto3>=1.34.0`

---

### Task 2: Add Backup Configuration Settings

**Why**: Centralize backup configuration (paths, S3 settings) in the existing settings module.

**Mirror**: `backend/app/config.py:47-68` (Settings class pattern)

**File**: `management-ui/backend/app/config.py`

**Do**:
Add these fields to the Settings class before `class Config:`:
```python
    # Backup settings
    BACKUP_LOCAL_PATH: str = os.path.join(os.environ.get("COMPOSE_BASE_PATH", "."), "backups")
    BACKUP_S3_ENDPOINT: str = os.environ.get("BACKUP_S3_ENDPOINT", "http://minio:9000")
    BACKUP_S3_BUCKET: str = os.environ.get("BACKUP_S3_BUCKET", "backups")
    BACKUP_S3_ACCESS_KEY: str = os.environ.get("BACKUP_S3_ACCESS_KEY", "minio")
    BACKUP_S3_SECRET_KEY: str = os.environ.get("BACKUP_S3_SECRET_KEY", "")
    BACKUP_RETENTION_DAYS: int = int(os.environ.get("BACKUP_RETENTION_DAYS", "30"))
```

**Don't**:
- Don't hardcode secrets - use environment variables

**Verify**: `python -c "from app.config import settings; print(settings.BACKUP_LOCAL_PATH)"`

---

### Task 3: Create Backup Schemas

**Why**: Define Pydantic models for backup API requests/responses.

**Mirror**: `backend/app/schemas/config.py:43-60`

**File**: `management-ui/backend/app/schemas/backup.py`

**Do**:
```python
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


class BackupDestination(str, Enum):
    LOCAL = "local"
    S3 = "s3"


class BackupType(str, Enum):
    FULL = "full"           # All volumes
    SERVICE = "service"     # Single service
    CONFIG = "config"       # Configuration files only


class BackupStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ScheduleFrequency(str, Enum):
    MANUAL = "manual"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"


class VolumeInfo(BaseModel):
    """Information about a Docker volume."""
    name: str
    service: str
    size_bytes: Optional[int] = None
    backup_strategy: str  # "pg_dump", "file_copy", "skip"
    last_backup: Optional[str] = None


class BackupInfo(BaseModel):
    """Information about a single backup."""
    id: str
    filename: str
    created: str
    size_bytes: int
    backup_type: BackupType
    destination: BackupDestination
    services: List[str]
    status: BackupStatus
    checksum: Optional[str] = None
    error: Optional[str] = None


class BackupJobInfo(BaseModel):
    """Information about a backup job (in progress or scheduled)."""
    id: str
    status: BackupStatus
    progress: int  # 0-100
    current_step: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class ScheduleConfig(BaseModel):
    """Backup schedule configuration."""
    enabled: bool = False
    frequency: ScheduleFrequency = ScheduleFrequency.DAILY
    hour: int = 2  # Hour of day (0-23) for daily/weekly
    day_of_week: int = 0  # Day of week (0=Monday) for weekly
    destination: BackupDestination = BackupDestination.LOCAL
    services: List[str] = []  # Empty = all services


class S3Config(BaseModel):
    """S3/MinIO configuration."""
    endpoint: str
    bucket: str
    access_key: str
    secret_key: str
    region: str = "us-east-1"


# Request models
class CreateBackupRequest(BaseModel):
    """Request to create a new backup."""
    services: List[str] = []  # Empty = all services
    destination: BackupDestination = BackupDestination.LOCAL
    backup_type: BackupType = BackupType.FULL


class RestoreBackupRequest(BaseModel):
    """Request to restore from a backup."""
    backup_id: str
    services: List[str] = []  # Empty = all services in backup
    stop_services: bool = True  # Stop services before restore


class UpdateScheduleRequest(BaseModel):
    """Request to update backup schedule."""
    schedule: ScheduleConfig


class TestS3Request(BaseModel):
    """Request to test S3 connection."""
    endpoint: str
    bucket: str
    access_key: str
    secret_key: str


# Response models
class BackupListResponse(BaseModel):
    """Response with list of backups."""
    backups: List[BackupInfo]
    total_size_bytes: int


class VolumeListResponse(BaseModel):
    """Response with list of volumes."""
    volumes: List[VolumeInfo]


class BackupJobResponse(BaseModel):
    """Response for backup job status."""
    job: BackupJobInfo


class ScheduleResponse(BaseModel):
    """Response with schedule configuration."""
    schedule: ScheduleConfig


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    success: bool = True


class S3TestResponse(BaseModel):
    """Response for S3 connection test."""
    success: bool
    message: str
    buckets: List[str] = []
```

**Don't**:
- Don't duplicate the existing BackupInfo from config.py - this is for volume backups

**Verify**: `python -c "from app.schemas.backup import BackupInfo; print(BackupInfo.model_fields)"`

---

### Task 4: Create Core Backup Manager

**Why**: Main business logic for backup/restore operations.

**Mirror**: `backend/app/core/env_manager.py` (class structure, error handling)

**File**: `management-ui/backend/app/core/backup_manager.py`

**Do**:
```python
"""
Backup manager for Docker volumes.

Supports:
- Database-aware backups (pg_dump for PostgreSQL)
- File-level backups for other volumes
- Local and S3/MinIO destinations
- Checksum verification
"""

import os
import json
import gzip
import hashlib
import subprocess
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Generator
from dataclasses import dataclass, asdict
import logging

import docker
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from ..config import settings

logger = logging.getLogger(__name__)


# Volume backup strategies
BACKUP_STRATEGIES = {
    # PostgreSQL databases - use pg_dump
    "langfuse_postgres_data": "pg_dump",
    "db-data": "pg_dump",  # Supabase db

    # Skip these (temporary or regenerable)
    "langfuse_clickhouse_logs": "skip",
    "caddy-config": "skip",

    # Everything else - file copy
    "default": "file_copy"
}

# Service to volume mapping
SERVICE_VOLUMES = {
    "n8n": ["n8n_storage"],
    "ollama": ["ollama_storage"],
    "open-webui": ["open-webui"],
    "flowise": ["flowise"],
    "qdrant": ["qdrant_storage"],
    "neo4j": ["neo4j_data"],  # bind mount actually
    "postgres": ["langfuse_postgres_data"],
    "db": ["db-data"],  # Supabase
    "redis": ["valkey-data"],
    "minio": ["langfuse_minio_data"],
    "clickhouse": ["langfuse_clickhouse_data"],
    "caddy": ["caddy-data"],
}

# Database connection info for pg_dump
DB_CONFIGS = {
    "langfuse_postgres_data": {
        "container": "postgres",
        "user": "postgres",
        "database": "postgres",
        "password_env": "POSTGRES_PASSWORD"
    },
    "db-data": {
        "container": "supabase-db",
        "user": "postgres",
        "database": "postgres",
        "password_env": "POSTGRES_PASSWORD"
    }
}


@dataclass
class BackupMetadata:
    """Metadata stored with each backup."""
    id: str
    created: str
    backup_type: str
    destination: str
    services: List[str]
    volumes: List[str]
    checksums: Dict[str, str]  # filename -> checksum
    size_bytes: int
    docker_compose_version: str

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "BackupMetadata":
        return cls(**data)


class BackupManager:
    """Manages Docker volume backups and restores."""

    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or settings.COMPOSE_BASE_PATH)
        self.backup_path = Path(settings.BACKUP_LOCAL_PATH)
        self.backup_path.mkdir(parents=True, exist_ok=True)

        self.docker = docker.from_env()
        self.project = settings.COMPOSE_PROJECT_NAME

    def list_volumes(self) -> List[Dict]:
        """List all project volumes with backup info."""
        volumes = []

        for volume in self.docker.volumes.list():
            labels = volume.attrs.get("Labels", {}) or {}
            if labels.get("com.docker.compose.project") == self.project:
                vol_name = volume.name
                service = labels.get("com.docker.compose.volume", vol_name)

                # Get strategy
                strategy = BACKUP_STRATEGIES.get(
                    vol_name.replace(f"{self.project}_", ""),
                    BACKUP_STRATEGIES["default"]
                )

                volumes.append({
                    "name": vol_name,
                    "service": service,
                    "backup_strategy": strategy,
                    "size_bytes": self._get_volume_size(vol_name),
                    "last_backup": self._get_last_backup_time(vol_name)
                })

        return volumes

    def _get_volume_size(self, volume_name: str) -> Optional[int]:
        """Get approximate size of a volume."""
        try:
            result = subprocess.run(
                ["docker", "run", "--rm", "-v", f"{volume_name}:/data",
                 "alpine", "du", "-sb", "/data"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return int(result.stdout.split()[0])
        except Exception as e:
            logger.warning(f"Failed to get volume size for {volume_name}: {e}")
        return None

    def _get_last_backup_time(self, volume_name: str) -> Optional[str]:
        """Get timestamp of last backup for a volume."""
        # Look through backup metadata files
        for meta_file in self.backup_path.glob("*.meta.json"):
            try:
                with open(meta_file) as f:
                    meta = json.load(f)
                    if volume_name in meta.get("volumes", []):
                        return meta.get("created")
            except Exception:
                pass
        return None

    def create_backup(
        self,
        services: List[str] = None,
        destination: str = "local",
        progress_callback: callable = None
    ) -> Tuple[str, BackupMetadata]:
        """
        Create a backup of specified services (or all if not specified).

        Args:
            services: List of service names to backup (None = all)
            destination: "local" or "s3"
            progress_callback: Optional callback(step, percent, message)

        Returns:
            Tuple of (backup_id, metadata)
        """
        backup_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.backup_path / backup_id
        backup_dir.mkdir(parents=True, exist_ok=True)

        def progress(step: str, percent: int, msg: str):
            if progress_callback:
                progress_callback(step, percent, msg)
            logger.info(f"Backup {backup_id}: [{percent}%] {step} - {msg}")

        try:
            # Determine volumes to backup
            volumes_to_backup = self._get_volumes_for_services(services)
            progress("init", 5, f"Will backup {len(volumes_to_backup)} volumes")

            checksums = {}
            total_size = 0

            for i, vol_info in enumerate(volumes_to_backup):
                vol_name = vol_info["name"]
                strategy = vol_info["backup_strategy"]

                percent = 10 + int((i / len(volumes_to_backup)) * 80)
                progress("backup", percent, f"Backing up {vol_name} ({strategy})")

                if strategy == "skip":
                    continue
                elif strategy == "pg_dump":
                    backup_file = self._backup_postgres(vol_name, backup_dir)
                else:
                    backup_file = self._backup_volume_files(vol_name, backup_dir)

                if backup_file:
                    checksums[backup_file.name] = self._calculate_checksum(backup_file)
                    total_size += backup_file.stat().st_size

            # Create metadata
            metadata = BackupMetadata(
                id=backup_id,
                created=datetime.now().isoformat(),
                backup_type="full" if not services else "service",
                destination=destination,
                services=services or list(SERVICE_VOLUMES.keys()),
                volumes=[v["name"] for v in volumes_to_backup],
                checksums=checksums,
                size_bytes=total_size,
                docker_compose_version=self._get_compose_version()
            )

            # Save metadata
            meta_file = backup_dir / "backup.meta.json"
            with open(meta_file, "w") as f:
                json.dump(metadata.to_dict(), f, indent=2)

            progress("finalize", 95, "Finalizing backup")

            # Upload to S3 if requested
            if destination == "s3":
                progress("upload", 97, "Uploading to S3")
                self._upload_to_s3(backup_dir, backup_id)
                # Optionally remove local copy after S3 upload
                # shutil.rmtree(backup_dir)

            progress("complete", 100, f"Backup {backup_id} completed")
            return backup_id, metadata

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            # Cleanup partial backup
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            raise

    def _get_volumes_for_services(self, services: List[str] = None) -> List[Dict]:
        """Get volumes that need to be backed up for specified services."""
        all_volumes = self.list_volumes()

        if not services:
            return all_volumes

        target_volumes = set()
        for service in services:
            if service in SERVICE_VOLUMES:
                for vol in SERVICE_VOLUMES[service]:
                    target_volumes.add(f"{self.project}_{vol}")

        return [v for v in all_volumes if v["name"] in target_volumes]

    def _backup_postgres(self, volume_name: str, backup_dir: Path) -> Optional[Path]:
        """Backup PostgreSQL database using pg_dump."""
        short_name = volume_name.replace(f"{self.project}_", "")
        db_config = DB_CONFIGS.get(short_name)

        if not db_config:
            logger.warning(f"No DB config for {volume_name}, falling back to file copy")
            return self._backup_volume_files(volume_name, backup_dir)

        # Load env for password
        env_file = self.base_path / ".env"
        password = ""
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    if line.startswith(db_config["password_env"]):
                        password = line.split("=", 1)[1].strip()
                        break

        backup_file = backup_dir / f"{short_name}.sql.gz"

        try:
            # Run pg_dump in the container
            cmd = [
                "docker", "exec",
                "-e", f"PGPASSWORD={password}",
                db_config["container"],
                "pg_dump",
                "-U", db_config["user"],
                "-d", db_config["database"],
                "--no-owner",
                "--no-acl"
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=600)

            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr.decode()}")

            # Compress and save
            with gzip.open(backup_file, "wb") as f:
                f.write(result.stdout)

            logger.info(f"PostgreSQL backup created: {backup_file}")
            return backup_file

        except Exception as e:
            logger.error(f"PostgreSQL backup failed for {volume_name}: {e}")
            # Fall back to file copy
            return self._backup_volume_files(volume_name, backup_dir)

    def _backup_volume_files(self, volume_name: str, backup_dir: Path) -> Optional[Path]:
        """Backup volume by copying files using a temporary container."""
        short_name = volume_name.replace(f"{self.project}_", "")
        backup_file = backup_dir / f"{short_name}.tar.gz"

        try:
            # Create tar archive using alpine container
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{volume_name}:/source:ro",
                "-v", f"{backup_dir}:/backup",
                "alpine",
                "tar", "czf", f"/backup/{short_name}.tar.gz", "-C", "/source", "."
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=600)

            if result.returncode != 0:
                raise Exception(f"tar failed: {result.stderr.decode()}")

            logger.info(f"Volume backup created: {backup_file}")
            return backup_file

        except Exception as e:
            logger.error(f"Volume backup failed for {volume_name}: {e}")
            return None

    def _calculate_checksum(self, filepath: Path) -> str:
        """Calculate SHA256 checksum of a file."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _get_compose_version(self) -> str:
        """Get docker compose version."""
        try:
            result = subprocess.run(
                ["docker", "compose", "version", "--short"],
                capture_output=True, text=True
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def _upload_to_s3(self, backup_dir: Path, backup_id: str):
        """Upload backup directory to S3/MinIO."""
        s3 = boto3.client(
            "s3",
            endpoint_url=settings.BACKUP_S3_ENDPOINT,
            aws_access_key_id=settings.BACKUP_S3_ACCESS_KEY,
            aws_secret_access_key=settings.BACKUP_S3_SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1"
        )

        # Ensure bucket exists
        try:
            s3.head_bucket(Bucket=settings.BACKUP_S3_BUCKET)
        except ClientError:
            s3.create_bucket(Bucket=settings.BACKUP_S3_BUCKET)

        # Upload all files in backup directory
        for filepath in backup_dir.iterdir():
            s3_key = f"{backup_id}/{filepath.name}"
            s3.upload_file(str(filepath), settings.BACKUP_S3_BUCKET, s3_key)
            logger.info(f"Uploaded {filepath.name} to s3://{settings.BACKUP_S3_BUCKET}/{s3_key}")

    def list_backups(self) -> List[Dict]:
        """List all available backups."""
        backups = []

        # Local backups
        for meta_file in self.backup_path.glob("*/backup.meta.json"):
            try:
                with open(meta_file) as f:
                    meta = json.load(f)
                    meta["location"] = "local"
                    backups.append(meta)
            except Exception as e:
                logger.warning(f"Failed to read backup metadata {meta_file}: {e}")

        # S3 backups (if configured)
        if settings.BACKUP_S3_SECRET_KEY:
            try:
                s3_backups = self._list_s3_backups()
                backups.extend(s3_backups)
            except Exception as e:
                logger.warning(f"Failed to list S3 backups: {e}")

        # Sort by creation time, newest first
        backups.sort(key=lambda x: x.get("created", ""), reverse=True)
        return backups

    def _list_s3_backups(self) -> List[Dict]:
        """List backups stored in S3."""
        s3 = boto3.client(
            "s3",
            endpoint_url=settings.BACKUP_S3_ENDPOINT,
            aws_access_key_id=settings.BACKUP_S3_ACCESS_KEY,
            aws_secret_access_key=settings.BACKUP_S3_SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1"
        )

        backups = []
        try:
            # List all "directories" (backup IDs)
            response = s3.list_objects_v2(
                Bucket=settings.BACKUP_S3_BUCKET,
                Delimiter="/"
            )

            for prefix in response.get("CommonPrefixes", []):
                backup_id = prefix["Prefix"].rstrip("/")

                # Try to get metadata
                try:
                    meta_obj = s3.get_object(
                        Bucket=settings.BACKUP_S3_BUCKET,
                        Key=f"{backup_id}/backup.meta.json"
                    )
                    meta = json.loads(meta_obj["Body"].read())
                    meta["location"] = "s3"
                    backups.append(meta)
                except ClientError:
                    # No metadata, create basic entry
                    backups.append({
                        "id": backup_id,
                        "location": "s3",
                        "created": backup_id  # ID is timestamp
                    })

        except ClientError as e:
            logger.warning(f"S3 list failed: {e}")

        return backups

    def restore_backup(
        self,
        backup_id: str,
        services: List[str] = None,
        progress_callback: callable = None
    ) -> bool:
        """
        Restore from a backup.

        Args:
            backup_id: ID of backup to restore
            services: List of services to restore (None = all)
            progress_callback: Optional callback(step, percent, message)
        """
        def progress(step: str, percent: int, msg: str):
            if progress_callback:
                progress_callback(step, percent, msg)
            logger.info(f"Restore {backup_id}: [{percent}%] {step} - {msg}")

        backup_dir = self.backup_path / backup_id

        # Download from S3 if not local
        if not backup_dir.exists():
            progress("download", 5, "Downloading from S3")
            self._download_from_s3(backup_id, backup_dir)

        # Load metadata
        meta_file = backup_dir / "backup.meta.json"
        if not meta_file.exists():
            raise FileNotFoundError(f"Backup metadata not found: {backup_id}")

        with open(meta_file) as f:
            metadata = json.load(f)

        progress("verify", 10, "Verifying backup integrity")

        # Verify checksums
        checksums = metadata.get("checksums", {})
        for filename, expected_checksum in checksums.items():
            filepath = backup_dir / filename
            if filepath.exists():
                actual_checksum = self._calculate_checksum(filepath)
                if actual_checksum != expected_checksum:
                    raise ValueError(f"Checksum mismatch for {filename}")

        progress("restore", 20, "Starting restore")

        # Restore each volume
        volumes_to_restore = metadata.get("volumes", [])
        if services:
            target_volumes = set()
            for service in services:
                if service in SERVICE_VOLUMES:
                    for vol in SERVICE_VOLUMES[service]:
                        target_volumes.add(f"{self.project}_{vol}")
            volumes_to_restore = [v for v in volumes_to_restore if v in target_volumes]

        for i, volume_name in enumerate(volumes_to_restore):
            percent = 20 + int((i / len(volumes_to_restore)) * 70)
            progress("restore", percent, f"Restoring {volume_name}")

            short_name = volume_name.replace(f"{self.project}_", "")

            # Check for PostgreSQL backup
            sql_file = backup_dir / f"{short_name}.sql.gz"
            tar_file = backup_dir / f"{short_name}.tar.gz"

            if sql_file.exists():
                self._restore_postgres(volume_name, sql_file)
            elif tar_file.exists():
                self._restore_volume_files(volume_name, tar_file)
            else:
                logger.warning(f"No backup file found for {volume_name}")

        progress("complete", 100, "Restore completed")
        return True

    def _restore_postgres(self, volume_name: str, backup_file: Path):
        """Restore PostgreSQL database from pg_dump backup."""
        short_name = volume_name.replace(f"{self.project}_", "")
        db_config = DB_CONFIGS.get(short_name)

        if not db_config:
            logger.error(f"No DB config for {volume_name}")
            return

        # Load env for password
        env_file = self.base_path / ".env"
        password = ""
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    if line.startswith(db_config["password_env"]):
                        password = line.split("=", 1)[1].strip()
                        break

        # Decompress and pipe to psql
        with gzip.open(backup_file, "rb") as f:
            sql_data = f.read()

        cmd = [
            "docker", "exec", "-i",
            "-e", f"PGPASSWORD={password}",
            db_config["container"],
            "psql",
            "-U", db_config["user"],
            "-d", db_config["database"]
        ]

        result = subprocess.run(cmd, input=sql_data, capture_output=True, timeout=600)

        if result.returncode != 0:
            logger.error(f"psql restore failed: {result.stderr.decode()}")
            raise Exception(f"PostgreSQL restore failed for {volume_name}")

        logger.info(f"PostgreSQL restored: {volume_name}")

    def _restore_volume_files(self, volume_name: str, backup_file: Path):
        """Restore volume from tar.gz backup."""
        short_name = volume_name.replace(f"{self.project}_", "")

        # Ensure volume exists
        try:
            self.docker.volumes.get(volume_name)
        except docker.errors.NotFound:
            self.docker.volumes.create(volume_name, labels={
                "com.docker.compose.project": self.project
            })

        # Extract using alpine container
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{volume_name}:/target",
            "-v", f"{backup_file.parent}:/backup:ro",
            "alpine",
            "sh", "-c", f"rm -rf /target/* && tar xzf /backup/{backup_file.name} -C /target"
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=600)

        if result.returncode != 0:
            raise Exception(f"Volume restore failed: {result.stderr.decode()}")

        logger.info(f"Volume restored: {volume_name}")

    def _download_from_s3(self, backup_id: str, backup_dir: Path):
        """Download backup from S3."""
        backup_dir.mkdir(parents=True, exist_ok=True)

        s3 = boto3.client(
            "s3",
            endpoint_url=settings.BACKUP_S3_ENDPOINT,
            aws_access_key_id=settings.BACKUP_S3_ACCESS_KEY,
            aws_secret_access_key=settings.BACKUP_S3_SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1"
        )

        response = s3.list_objects_v2(
            Bucket=settings.BACKUP_S3_BUCKET,
            Prefix=f"{backup_id}/"
        )

        for obj in response.get("Contents", []):
            key = obj["Key"]
            filename = key.split("/")[-1]
            if filename:
                local_path = backup_dir / filename
                s3.download_file(settings.BACKUP_S3_BUCKET, key, str(local_path))
                logger.info(f"Downloaded {key}")

    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup."""
        # Delete local
        backup_dir = self.backup_path / backup_id
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
            logger.info(f"Deleted local backup: {backup_id}")

        # Delete from S3
        if settings.BACKUP_S3_SECRET_KEY:
            try:
                s3 = boto3.client(
                    "s3",
                    endpoint_url=settings.BACKUP_S3_ENDPOINT,
                    aws_access_key_id=settings.BACKUP_S3_ACCESS_KEY,
                    aws_secret_access_key=settings.BACKUP_S3_SECRET_KEY,
                    config=Config(signature_version="s3v4"),
                    region_name="us-east-1"
                )

                response = s3.list_objects_v2(
                    Bucket=settings.BACKUP_S3_BUCKET,
                    Prefix=f"{backup_id}/"
                )

                for obj in response.get("Contents", []):
                    s3.delete_object(Bucket=settings.BACKUP_S3_BUCKET, Key=obj["Key"])

                logger.info(f"Deleted S3 backup: {backup_id}")
            except Exception as e:
                logger.warning(f"Failed to delete S3 backup: {e}")

        return True

    def verify_backup(self, backup_id: str) -> Dict:
        """Verify backup integrity."""
        backup_dir = self.backup_path / backup_id

        if not backup_dir.exists():
            return {"valid": False, "error": "Backup not found locally"}

        meta_file = backup_dir / "backup.meta.json"
        if not meta_file.exists():
            return {"valid": False, "error": "Metadata not found"}

        with open(meta_file) as f:
            metadata = json.load(f)

        checksums = metadata.get("checksums", {})
        errors = []

        for filename, expected in checksums.items():
            filepath = backup_dir / filename
            if not filepath.exists():
                errors.append(f"Missing file: {filename}")
                continue

            actual = self._calculate_checksum(filepath)
            if actual != expected:
                errors.append(f"Checksum mismatch: {filename}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "files_checked": len(checksums)
        }

    def test_s3_connection(
        self,
        endpoint: str,
        bucket: str,
        access_key: str,
        secret_key: str
    ) -> Dict:
        """Test S3/MinIO connection."""
        try:
            s3 = boto3.client(
                "s3",
                endpoint_url=endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=Config(signature_version="s3v4"),
                region_name="us-east-1"
            )

            # List buckets to verify connection
            response = s3.list_buckets()
            buckets = [b["Name"] for b in response.get("Buckets", [])]

            # Check if target bucket exists
            bucket_exists = bucket in buckets

            return {
                "success": True,
                "message": f"Connected successfully. Bucket '{bucket}' {'exists' if bucket_exists else 'will be created'}.",
                "buckets": buckets
            }

        except ClientError as e:
            return {
                "success": False,
                "message": f"Connection failed: {e.response['Error']['Message']}",
                "buckets": []
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}",
                "buckets": []
            }
```

**Don't**:
- Don't backup running databases with file copy (use pg_dump)
- Don't store secrets in backup metadata
- Don't use synchronous operations for large backups (use threading/async later)

**Verify**: `python -c "from app.core.backup_manager import BackupManager; print('Import OK')"`

---

### Task 5: Create Backup Scheduler

**Why**: Support automated scheduled backups.

**Mirror**: Simple scheduler without external dependencies

**File**: `management-ui/backend/app/core/backup_scheduler.py`

**Do**:
```python
"""
Simple backup scheduler using threading.

For production use, consider external schedulers like cron or APScheduler.
"""

import threading
import time
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass, asdict

from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class ScheduleConfig:
    """Backup schedule configuration."""
    enabled: bool = False
    frequency: str = "daily"  # manual, hourly, daily, weekly
    hour: int = 2  # Hour of day (0-23)
    day_of_week: int = 0  # Monday = 0
    destination: str = "local"
    services: list = None  # None = all

    def __post_init__(self):
        if self.services is None:
            self.services = []


class BackupScheduler:
    """Simple backup scheduler."""

    CONFIG_FILE = "backup_schedule.json"

    def __init__(self, backup_manager, base_path: str = None):
        self.backup_manager = backup_manager
        self.base_path = Path(base_path or settings.COMPOSE_BASE_PATH)
        self.config_file = self.base_path / "data" / self.CONFIG_FILE

        self._schedule: Optional[ScheduleConfig] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_run: Optional[datetime] = None

        self._load_config()

    def _load_config(self):
        """Load schedule configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    data = json.load(f)
                    self._schedule = ScheduleConfig(**data.get("schedule", {}))
                    self._last_run = data.get("last_run")
                    if self._last_run:
                        self._last_run = datetime.fromisoformat(self._last_run)
            except Exception as e:
                logger.error(f"Failed to load schedule config: {e}")
                self._schedule = ScheduleConfig()
        else:
            self._schedule = ScheduleConfig()

    def _save_config(self):
        """Save schedule configuration to file."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "schedule": asdict(self._schedule),
            "last_run": self._last_run.isoformat() if self._last_run else None
        }

        with open(self.config_file, "w") as f:
            json.dump(data, f, indent=2)

    def get_schedule(self) -> ScheduleConfig:
        """Get current schedule configuration."""
        return self._schedule

    def update_schedule(self, config: ScheduleConfig):
        """Update schedule configuration."""
        self._schedule = config
        self._save_config()

        # Restart scheduler if running
        if self._thread and self._thread.is_alive():
            self.stop()
            if config.enabled:
                self.start()

    def get_next_run(self) -> Optional[datetime]:
        """Calculate next scheduled run time."""
        if not self._schedule or not self._schedule.enabled:
            return None

        now = datetime.now()

        if self._schedule.frequency == "manual":
            return None

        elif self._schedule.frequency == "hourly":
            next_run = now.replace(minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(hours=1)
            return next_run

        elif self._schedule.frequency == "daily":
            next_run = now.replace(
                hour=self._schedule.hour,
                minute=0, second=0, microsecond=0
            )
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run

        elif self._schedule.frequency == "weekly":
            next_run = now.replace(
                hour=self._schedule.hour,
                minute=0, second=0, microsecond=0
            )
            days_ahead = self._schedule.day_of_week - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_run += timedelta(days=days_ahead)
            if next_run <= now:
                next_run += timedelta(weeks=1)
            return next_run

        return None

    def start(self):
        """Start the scheduler thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("Scheduler already running")
            return

        if not self._schedule or not self._schedule.enabled:
            logger.info("Schedule not enabled, not starting")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Backup scheduler started")

    def stop(self):
        """Stop the scheduler thread."""
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=5)
            logger.info("Backup scheduler stopped")

    def _run_loop(self):
        """Main scheduler loop."""
        while not self._stop_event.is_set():
            try:
                next_run = self.get_next_run()

                if next_run:
                    # Sleep until next run (check every minute)
                    while datetime.now() < next_run and not self._stop_event.is_set():
                        time.sleep(60)

                    if not self._stop_event.is_set():
                        self._execute_backup()
                else:
                    # No schedule, sleep and check again
                    time.sleep(60)

            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)

    def _execute_backup(self):
        """Execute scheduled backup."""
        logger.info("Executing scheduled backup")

        try:
            services = self._schedule.services if self._schedule.services else None
            destination = self._schedule.destination

            backup_id, metadata = self.backup_manager.create_backup(
                services=services,
                destination=destination
            )

            self._last_run = datetime.now()
            self._save_config()

            logger.info(f"Scheduled backup completed: {backup_id}")

        except Exception as e:
            logger.error(f"Scheduled backup failed: {e}")

    def run_now(self) -> str:
        """Run backup immediately (manual trigger)."""
        services = self._schedule.services if self._schedule.services else None
        destination = self._schedule.destination

        backup_id, metadata = self.backup_manager.create_backup(
            services=services,
            destination=destination
        )

        return backup_id
```

**Don't**:
- Don't use complex scheduling libraries (keep it simple)
- Don't persist scheduler state across restarts (reload on startup)

**Verify**: `python -c "from app.core.backup_scheduler import BackupScheduler; print('Import OK')"`

---

### Task 6: Create Backup API Routes

**Why**: Expose backup functionality through REST API.

**Mirror**: `backend/app/api/routes/config.py` (route structure, auth)

**File**: `management-ui/backend/app/api/routes/backup.py`

**Do**:
```python
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import Optional

from ...schemas.backup import (
    BackupListResponse, VolumeListResponse, BackupJobResponse,
    ScheduleResponse, MessageResponse, S3TestResponse,
    CreateBackupRequest, RestoreBackupRequest, UpdateScheduleRequest,
    TestS3Request, BackupInfo, VolumeInfo, BackupJobInfo, ScheduleConfig,
    BackupStatus
)
from ...core.backup_manager import BackupManager
from ...core.backup_scheduler import BackupScheduler
from ..deps import get_backup_manager, get_backup_scheduler, get_current_user
from ...config import settings

router = APIRouter()

# In-memory job tracking (could be moved to Redis/DB for persistence)
_active_jobs = {}


@router.get("/volumes", response_model=VolumeListResponse)
async def list_volumes(
    backup_manager: BackupManager = Depends(get_backup_manager),
    _: dict = Depends(get_current_user)
):
    """List all Docker volumes with backup information."""
    volumes = backup_manager.list_volumes()
    return VolumeListResponse(volumes=[VolumeInfo(**v) for v in volumes])


@router.get("", response_model=BackupListResponse)
async def list_backups(
    backup_manager: BackupManager = Depends(get_backup_manager),
    _: dict = Depends(get_current_user)
):
    """List all available backups."""
    backups = backup_manager.list_backups()
    total_size = sum(b.get("size_bytes", 0) for b in backups)
    return BackupListResponse(
        backups=[BackupInfo(
            id=b["id"],
            filename=f"{b['id']}.tar.gz",
            created=b["created"],
            size_bytes=b.get("size_bytes", 0),
            backup_type=b.get("backup_type", "full"),
            destination=b.get("destination", "local"),
            services=b.get("services", []),
            status=BackupStatus.COMPLETED,
            checksum=None
        ) for b in backups],
        total_size_bytes=total_size
    )


@router.post("", response_model=BackupJobResponse)
async def create_backup(
    request: CreateBackupRequest,
    background_tasks: BackgroundTasks,
    backup_manager: BackupManager = Depends(get_backup_manager),
    _: dict = Depends(get_current_user)
):
    """Create a new backup (runs in background)."""
    from datetime import datetime

    job_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create job info
    job = BackupJobInfo(
        id=job_id,
        status=BackupStatus.PENDING,
        progress=0,
        current_step="Starting backup",
        started_at=datetime.now().isoformat()
    )
    _active_jobs[job_id] = job

    def run_backup():
        def progress_callback(step, percent, message):
            _active_jobs[job_id].current_step = message
            _active_jobs[job_id].progress = percent
            _active_jobs[job_id].status = BackupStatus.IN_PROGRESS

        try:
            backup_id, metadata = backup_manager.create_backup(
                services=request.services if request.services else None,
                destination=request.destination.value,
                progress_callback=progress_callback
            )
            _active_jobs[job_id].status = BackupStatus.COMPLETED
            _active_jobs[job_id].progress = 100
            _active_jobs[job_id].completed_at = datetime.now().isoformat()
        except Exception as e:
            _active_jobs[job_id].status = BackupStatus.FAILED
            _active_jobs[job_id].error = str(e)

    background_tasks.add_task(run_backup)

    return BackupJobResponse(job=job)


@router.get("/jobs/{job_id}", response_model=BackupJobResponse)
async def get_job_status(
    job_id: str,
    _: dict = Depends(get_current_user)
):
    """Get status of a backup job."""
    if job_id not in _active_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    return BackupJobResponse(job=_active_jobs[job_id])


@router.post("/{backup_id}/restore", response_model=BackupJobResponse)
async def restore_backup(
    backup_id: str,
    request: RestoreBackupRequest,
    background_tasks: BackgroundTasks,
    backup_manager: BackupManager = Depends(get_backup_manager),
    _: dict = Depends(get_current_user)
):
    """Restore from a backup (runs in background)."""
    from datetime import datetime

    job_id = f"restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    job = BackupJobInfo(
        id=job_id,
        status=BackupStatus.PENDING,
        progress=0,
        current_step="Starting restore",
        started_at=datetime.now().isoformat()
    )
    _active_jobs[job_id] = job

    def run_restore():
        def progress_callback(step, percent, message):
            _active_jobs[job_id].current_step = message
            _active_jobs[job_id].progress = percent
            _active_jobs[job_id].status = BackupStatus.IN_PROGRESS

        try:
            backup_manager.restore_backup(
                backup_id=backup_id,
                services=request.services if request.services else None,
                progress_callback=progress_callback
            )
            _active_jobs[job_id].status = BackupStatus.COMPLETED
            _active_jobs[job_id].progress = 100
            _active_jobs[job_id].completed_at = datetime.now().isoformat()
        except Exception as e:
            _active_jobs[job_id].status = BackupStatus.FAILED
            _active_jobs[job_id].error = str(e)

    background_tasks.add_task(run_restore)

    return BackupJobResponse(job=job)


@router.delete("/{backup_id}", response_model=MessageResponse)
async def delete_backup(
    backup_id: str,
    backup_manager: BackupManager = Depends(get_backup_manager),
    _: dict = Depends(get_current_user)
):
    """Delete a backup."""
    try:
        backup_manager.delete_backup(backup_id)
        return MessageResponse(message=f"Backup {backup_id} deleted")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{backup_id}/verify")
async def verify_backup(
    backup_id: str,
    backup_manager: BackupManager = Depends(get_backup_manager),
    _: dict = Depends(get_current_user)
):
    """Verify backup integrity."""
    result = backup_manager.verify_backup(backup_id)
    return result


@router.get("/schedule", response_model=ScheduleResponse)
async def get_schedule(
    scheduler: BackupScheduler = Depends(get_backup_scheduler),
    _: dict = Depends(get_current_user)
):
    """Get current backup schedule."""
    config = scheduler.get_schedule()
    return ScheduleResponse(schedule=ScheduleConfig(
        enabled=config.enabled,
        frequency=config.frequency,
        hour=config.hour,
        day_of_week=config.day_of_week,
        destination=config.destination,
        services=config.services
    ))


@router.put("/schedule", response_model=ScheduleResponse)
async def update_schedule(
    request: UpdateScheduleRequest,
    scheduler: BackupScheduler = Depends(get_backup_scheduler),
    _: dict = Depends(get_current_user)
):
    """Update backup schedule."""
    from ...core.backup_scheduler import ScheduleConfig as SC

    config = SC(
        enabled=request.schedule.enabled,
        frequency=request.schedule.frequency.value,
        hour=request.schedule.hour,
        day_of_week=request.schedule.day_of_week,
        destination=request.schedule.destination.value,
        services=request.schedule.services
    )
    scheduler.update_schedule(config)

    return ScheduleResponse(schedule=request.schedule)


@router.post("/test-s3", response_model=S3TestResponse)
async def test_s3_connection(
    request: TestS3Request,
    backup_manager: BackupManager = Depends(get_backup_manager),
    _: dict = Depends(get_current_user)
):
    """Test S3/MinIO connection."""
    result = backup_manager.test_s3_connection(
        endpoint=request.endpoint,
        bucket=request.bucket,
        access_key=request.access_key,
        secret_key=request.secret_key
    )
    return S3TestResponse(**result)
```

**Don't**:
- Don't run long operations synchronously (use background tasks)
- Don't expose internal paths or sensitive data

**Verify**: `python -c "from app.api.routes.backup import router; print('Routes:', [r.path for r in router.routes])"`

---

### Task 7: Update API Routes Init

**Why**: Register backup router in the API.

**Mirror**: `backend/app/api/routes/__init__.py`

**File**: `management-ui/backend/app/api/routes/__init__.py`

**Do**:
Add import and router registration:
```python
from .backup import router as backup_router

# Add to existing router registrations:
api_router.include_router(backup_router, prefix="/backup", tags=["backup"])
```

**Don't**:
- Don't remove existing routers

**Verify**: `python -c "from app.api.routes import api_router; print([r.path for r in api_router.routes if 'backup' in r.path])"`

---

### Task 8: Update Dependencies

**Why**: Add backup manager and scheduler as FastAPI dependencies.

**Mirror**: `backend/app/api/deps.py`

**File**: `management-ui/backend/app/api/deps.py`

**Do**:
Add these imports and functions:
```python
from ..core.backup_manager import BackupManager
from ..core.backup_scheduler import BackupScheduler

# Singleton instances
_backup_manager = None
_backup_scheduler = None

def get_backup_manager() -> BackupManager:
    """Get backup manager instance."""
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager(settings.COMPOSE_BASE_PATH)
    return _backup_manager

def get_backup_scheduler() -> BackupScheduler:
    """Get backup scheduler instance."""
    global _backup_scheduler
    if _backup_scheduler is None:
        _backup_scheduler = BackupScheduler(
            get_backup_manager(),
            settings.COMPOSE_BASE_PATH
        )
    return _backup_scheduler
```

**Don't**:
- Don't create new instances on every request (use singletons)

**Verify**: `python -c "from app.api.deps import get_backup_manager; print(get_backup_manager())"`

---

### Task 9: Create Frontend Types

**Why**: TypeScript type definitions for backup data.

**Mirror**: `frontend/src/types/config.ts`

**File**: `management-ui/frontend/src/types/backup.ts`

**Do**:
```typescript
export type BackupDestination = 'local' | 's3';
export type BackupType = 'full' | 'service' | 'config';
export type BackupStatus = 'pending' | 'in_progress' | 'completed' | 'failed';
export type ScheduleFrequency = 'manual' | 'hourly' | 'daily' | 'weekly';

export interface VolumeInfo {
  name: string;
  service: string;
  size_bytes: number | null;
  backup_strategy: string;
  last_backup: string | null;
}

export interface BackupInfo {
  id: string;
  filename: string;
  created: string;
  size_bytes: number;
  backup_type: BackupType;
  destination: BackupDestination;
  services: string[];
  status: BackupStatus;
  checksum: string | null;
  error: string | null;
}

export interface BackupJob {
  id: string;
  status: BackupStatus;
  progress: number;
  current_step: string;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
}

export interface ScheduleConfig {
  enabled: boolean;
  frequency: ScheduleFrequency;
  hour: number;
  day_of_week: number;
  destination: BackupDestination;
  services: string[];
}

export interface S3Config {
  endpoint: string;
  bucket: string;
  access_key: string;
  secret_key: string;
  region: string;
}
```

**Verify**: TypeScript compiler will check on build

---

### Task 10: Create Frontend API Client

**Why**: API client for backup endpoints.

**Mirror**: `frontend/src/api/config.ts`

**File**: `management-ui/frontend/src/api/backup.ts`

**Do**:
```typescript
import { apiClient } from './client';
import type {
  VolumeInfo,
  BackupInfo,
  BackupJob,
  ScheduleConfig,
  BackupDestination,
  BackupType,
} from '../types/backup';

export interface VolumeListResponse {
  volumes: VolumeInfo[];
}

export interface BackupListResponse {
  backups: BackupInfo[];
  total_size_bytes: number;
}

export interface BackupJobResponse {
  job: BackupJob;
}

export interface ScheduleResponse {
  schedule: ScheduleConfig;
}

export interface S3TestResponse {
  success: boolean;
  message: string;
  buckets: string[];
}

export const backupApi = {
  async listVolumes(): Promise<VolumeListResponse> {
    const response = await apiClient.get<VolumeListResponse>('/backup/volumes');
    return response.data;
  },

  async listBackups(): Promise<BackupListResponse> {
    const response = await apiClient.get<BackupListResponse>('/backup');
    return response.data;
  },

  async createBackup(
    services: string[] = [],
    destination: BackupDestination = 'local',
    backupType: BackupType = 'full'
  ): Promise<BackupJobResponse> {
    const response = await apiClient.post<BackupJobResponse>('/backup', {
      services,
      destination,
      backup_type: backupType,
    });
    return response.data;
  },

  async getJobStatus(jobId: string): Promise<BackupJobResponse> {
    const response = await apiClient.get<BackupJobResponse>(`/backup/jobs/${jobId}`);
    return response.data;
  },

  async restoreBackup(
    backupId: string,
    services: string[] = [],
    stopServices: boolean = true
  ): Promise<BackupJobResponse> {
    const response = await apiClient.post<BackupJobResponse>(
      `/backup/${backupId}/restore`,
      {
        backup_id: backupId,
        services,
        stop_services: stopServices,
      }
    );
    return response.data;
  },

  async deleteBackup(backupId: string): Promise<{ message: string }> {
    const response = await apiClient.delete(`/backup/${backupId}`);
    return response.data;
  },

  async verifyBackup(backupId: string): Promise<{ valid: boolean; errors: string[] }> {
    const response = await apiClient.get(`/backup/${backupId}/verify`);
    return response.data;
  },

  async getSchedule(): Promise<ScheduleResponse> {
    const response = await apiClient.get<ScheduleResponse>('/backup/schedule');
    return response.data;
  },

  async updateSchedule(schedule: ScheduleConfig): Promise<ScheduleResponse> {
    const response = await apiClient.put<ScheduleResponse>('/backup/schedule', {
      schedule,
    });
    return response.data;
  },

  async testS3Connection(
    endpoint: string,
    bucket: string,
    accessKey: string,
    secretKey: string
  ): Promise<S3TestResponse> {
    const response = await apiClient.post<S3TestResponse>('/backup/test-s3', {
      endpoint,
      bucket,
      access_key: accessKey,
      secret_key: secretKey,
    });
    return response.data;
  },
};
```

**Verify**: TypeScript compiler will check on build

---

### Task 11: Create Backup Zustand Store

**Why**: State management for backup UI.

**Mirror**: `frontend/src/store/configStore.ts`

**File**: `management-ui/frontend/src/store/backupStore.ts`

**Do**:
```typescript
import { create } from 'zustand';
import { backupApi } from '../api/backup';
import type {
  VolumeInfo,
  BackupInfo,
  BackupJob,
  ScheduleConfig,
  BackupDestination,
} from '../types/backup';

interface BackupState {
  volumes: VolumeInfo[];
  backups: BackupInfo[];
  schedule: ScheduleConfig | null;
  activeJob: BackupJob | null;
  isLoading: boolean;
  error: string | null;
  totalSizeBytes: number;

  fetchVolumes: () => Promise<void>;
  fetchBackups: () => Promise<void>;
  fetchSchedule: () => Promise<void>;
  createBackup: (services?: string[], destination?: BackupDestination) => Promise<string>;
  restoreBackup: (backupId: string, services?: string[]) => Promise<string>;
  deleteBackup: (backupId: string) => Promise<void>;
  verifyBackup: (backupId: string) => Promise<{ valid: boolean; errors: string[] }>;
  updateSchedule: (schedule: ScheduleConfig) => Promise<void>;
  pollJobStatus: (jobId: string) => Promise<void>;
  clearError: () => void;
}

export const useBackupStore = create<BackupState>((set, get) => ({
  volumes: [],
  backups: [],
  schedule: null,
  activeJob: null,
  isLoading: false,
  error: null,
  totalSizeBytes: 0,

  fetchVolumes: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await backupApi.listVolumes();
      set({ volumes: response.volumes, isLoading: false });
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      set({
        error: err.response?.data?.detail || 'Failed to fetch volumes',
        isLoading: false,
      });
    }
  },

  fetchBackups: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await backupApi.listBackups();
      set({
        backups: response.backups,
        totalSizeBytes: response.total_size_bytes,
        isLoading: false,
      });
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      set({
        error: err.response?.data?.detail || 'Failed to fetch backups',
        isLoading: false,
      });
    }
  },

  fetchSchedule: async () => {
    try {
      const response = await backupApi.getSchedule();
      set({ schedule: response.schedule });
    } catch (error: unknown) {
      console.error('Failed to fetch schedule:', error);
    }
  },

  createBackup: async (services = [], destination = 'local') => {
    set({ error: null });
    try {
      const response = await backupApi.createBackup(services, destination);
      set({ activeJob: response.job });
      return response.job.id;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      set({ error: err.response?.data?.detail || 'Failed to create backup' });
      throw error;
    }
  },

  restoreBackup: async (backupId, services = []) => {
    set({ error: null });
    try {
      const response = await backupApi.restoreBackup(backupId, services);
      set({ activeJob: response.job });
      return response.job.id;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      set({ error: err.response?.data?.detail || 'Failed to restore backup' });
      throw error;
    }
  },

  deleteBackup: async (backupId) => {
    try {
      await backupApi.deleteBackup(backupId);
      // Refresh list
      await get().fetchBackups();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      set({ error: err.response?.data?.detail || 'Failed to delete backup' });
      throw error;
    }
  },

  verifyBackup: async (backupId) => {
    try {
      return await backupApi.verifyBackup(backupId);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      set({ error: err.response?.data?.detail || 'Failed to verify backup' });
      throw error;
    }
  },

  updateSchedule: async (schedule) => {
    try {
      const response = await backupApi.updateSchedule(schedule);
      set({ schedule: response.schedule });
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      set({ error: err.response?.data?.detail || 'Failed to update schedule' });
      throw error;
    }
  },

  pollJobStatus: async (jobId) => {
    try {
      const response = await backupApi.getJobStatus(jobId);
      set({ activeJob: response.job });

      if (response.job.status === 'completed' || response.job.status === 'failed') {
        // Refresh backups list on completion
        if (response.job.status === 'completed') {
          await get().fetchBackups();
        }
      }
    } catch (error: unknown) {
      console.error('Failed to poll job status:', error);
    }
  },

  clearError: () => set({ error: null }),
}));
```

**Verify**: TypeScript compiler will check on build

---

### Task 12: Create VolumeBackupManager Component

**Why**: Main UI component for backup management.

**Mirror**: `frontend/src/components/config/BackupManager.tsx` structure

**File**: `management-ui/frontend/src/components/backup/VolumeBackupManager.tsx`

**Do**:
```typescript
import { useEffect, useState } from 'react';
import {
  HardDrive,
  Download,
  Upload,
  Trash2,
  CheckCircle,
  AlertCircle,
  Clock,
  RefreshCw,
  Play,
} from 'lucide-react';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import { useBackupStore } from '../../store/backupStore';
import type { BackupInfo, BackupDestination } from '../../types/backup';

export const VolumeBackupManager: React.FC = () => {
  const {
    backups,
    volumes,
    activeJob,
    isLoading,
    error,
    totalSizeBytes,
    fetchBackups,
    fetchVolumes,
    createBackup,
    restoreBackup,
    deleteBackup,
    verifyBackup,
    pollJobStatus,
    clearError,
  } = useBackupStore();

  const [selectedServices, setSelectedServices] = useState<string[]>([]);
  const [destination, setDestination] = useState<BackupDestination>('local');
  const [isCreating, setIsCreating] = useState(false);
  const [restoreTarget, setRestoreTarget] = useState<string | null>(null);

  useEffect(() => {
    fetchBackups();
    fetchVolumes();
  }, [fetchBackups, fetchVolumes]);

  // Poll job status when active
  useEffect(() => {
    if (activeJob && (activeJob.status === 'pending' || activeJob.status === 'in_progress')) {
      const interval = setInterval(() => {
        pollJobStatus(activeJob.id);
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [activeJob, pollJobStatus]);

  const handleCreateBackup = async () => {
    setIsCreating(true);
    try {
      await createBackup(selectedServices, destination);
    } catch {
      // Error handled by store
    } finally {
      setIsCreating(false);
    }
  };

  const handleRestore = async (backupId: string) => {
    if (!confirm('This will overwrite existing data. Are you sure?')) {
      return;
    }
    setRestoreTarget(backupId);
    try {
      await restoreBackup(backupId);
    } catch {
      // Error handled by store
    } finally {
      setRestoreTarget(null);
    }
  };

  const handleDelete = async (backupId: string) => {
    if (!confirm('Delete this backup permanently?')) {
      return;
    }
    try {
      await deleteBackup(backupId);
    } catch {
      // Error handled by store
    }
  };

  const handleVerify = async (backupId: string) => {
    const result = await verifyBackup(backupId);
    if (result.valid) {
      alert('Backup verified successfully!');
    } else {
      alert(`Backup verification failed:\n${result.errors.join('\n')}`);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-400" />;
      case 'in_progress':
        return <RefreshCw className="w-4 h-4 text-blue-400 animate-spin" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Error Banner */}
      {error && (
        <div className="flex items-center justify-between p-4 bg-red-900/20 border border-red-700/30 rounded-lg">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <span className="text-red-400">{error}</span>
          </div>
          <Button variant="ghost" size="sm" onClick={clearError}>
            Dismiss
          </Button>
        </div>
      )}

      {/* Active Job Progress */}
      {activeJob && activeJob.status !== 'completed' && (
        <Card>
          <div className="flex items-center gap-3 mb-3">
            {getStatusIcon(activeJob.status)}
            <h4 className="font-semibold text-white">
              {activeJob.id.startsWith('restore_') ? 'Restoring' : 'Creating Backup'}
            </h4>
          </div>
          <p className="text-gray-400 text-sm mb-2">{activeJob.current_step}</p>
          <div className="w-full bg-gray-700 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${activeJob.progress}%` }}
            />
          </div>
          <p className="text-gray-500 text-xs mt-1">{activeJob.progress}% complete</p>
          {activeJob.error && (
            <p className="text-red-400 text-sm mt-2">{activeJob.error}</p>
          )}
        </Card>
      )}

      {/* Create Backup Section */}
      <Card>
        <h4 className="font-semibold text-white mb-4 flex items-center gap-2">
          <Download className="w-5 h-5 text-blue-400" />
          Create Backup
        </h4>

        <div className="space-y-4">
          {/* Destination Selection */}
          <div>
            <label className="block text-sm text-gray-400 mb-2">Destination</label>
            <div className="flex gap-3">
              <button
                onClick={() => setDestination('local')}
                className={`px-4 py-2 rounded-lg border transition-colors ${
                  destination === 'local'
                    ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                    : 'border-gray-600 text-gray-400 hover:border-gray-500'
                }`}
              >
                Local Storage
              </button>
              <button
                onClick={() => setDestination('s3')}
                className={`px-4 py-2 rounded-lg border transition-colors ${
                  destination === 's3'
                    ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                    : 'border-gray-600 text-gray-400 hover:border-gray-500'
                }`}
              >
                S3 / MinIO
              </button>
            </div>
          </div>

          {/* Volume Selection */}
          <div>
            <label className="block text-sm text-gray-400 mb-2">
              Services to Backup (leave empty for all)
            </label>
            <div className="flex flex-wrap gap-2">
              {volumes.map((vol) => (
                <button
                  key={vol.name}
                  onClick={() => {
                    const service = vol.service;
                    setSelectedServices((prev) =>
                      prev.includes(service)
                        ? prev.filter((s) => s !== service)
                        : [...prev, service]
                    );
                  }}
                  className={`px-3 py-1 text-sm rounded-lg border transition-colors ${
                    selectedServices.includes(vol.service)
                      ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                      : 'border-gray-600 text-gray-400 hover:border-gray-500'
                  }`}
                >
                  {vol.service}
                  {vol.size_bytes && (
                    <span className="ml-1 text-xs text-gray-500">
                      ({formatSize(vol.size_bytes)})
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>

          <Button
            variant="primary"
            onClick={handleCreateBackup}
            disabled={isCreating || isLoading}
            isLoading={isCreating}
          >
            <Play className="w-4 h-4 mr-2" />
            Start Backup
          </Button>
        </div>
      </Card>

      {/* Backup List */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h4 className="font-semibold text-white flex items-center gap-2">
            <HardDrive className="w-5 h-5 text-gray-400" />
            Backups
            <span className="text-sm text-gray-500">
              ({backups.length} total, {formatSize(totalSizeBytes)})
            </span>
          </h4>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => fetchBackups()}
            disabled={isLoading}
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>

        {backups.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No backups yet</p>
        ) : (
          <div className="space-y-3">
            {backups.map((backup) => (
              <BackupItem
                key={backup.id}
                backup={backup}
                onRestore={() => handleRestore(backup.id)}
                onDelete={() => handleDelete(backup.id)}
                onVerify={() => handleVerify(backup.id)}
                isRestoring={restoreTarget === backup.id}
                formatSize={formatSize}
                formatDate={formatDate}
                getStatusIcon={getStatusIcon}
              />
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};

interface BackupItemProps {
  backup: BackupInfo;
  onRestore: () => void;
  onDelete: () => void;
  onVerify: () => void;
  isRestoring: boolean;
  formatSize: (bytes: number) => string;
  formatDate: (date: string) => string;
  getStatusIcon: (status: string) => React.ReactNode;
}

const BackupItem: React.FC<BackupItemProps> = ({
  backup,
  onRestore,
  onDelete,
  onVerify,
  isRestoring,
  formatSize,
  formatDate,
  getStatusIcon,
}) => {
  return (
    <div className="flex items-center justify-between p-4 bg-gray-800 rounded-lg hover:bg-gray-750 transition-colors">
      <div className="flex items-center gap-3">
        {getStatusIcon(backup.status)}
        <div>
          <p className="text-white font-medium">{backup.id}</p>
          <p className="text-gray-500 text-sm">
            {formatDate(backup.created)} - {formatSize(backup.size_bytes)}
            <span className="ml-2 text-gray-600">
              ({backup.destination === 's3' ? 'S3' : 'Local'})
            </span>
          </p>
          <p className="text-gray-600 text-xs">
            Services: {backup.services.join(', ') || 'All'}
          </p>
        </div>
      </div>
      <div className="flex gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={onVerify}
          title="Verify backup integrity"
        >
          <CheckCircle className="w-4 h-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={onRestore}
          disabled={isRestoring}
          title="Restore from backup"
        >
          <Upload className="w-4 h-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={onDelete}
          className="text-red-400 hover:text-red-300"
          title="Delete backup"
        >
          <Trash2 className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
};
```

**Verify**: TypeScript compiler will check on build

---

### Task 13: Create BackupScheduleConfig Component

**Why**: UI for configuring backup schedule.

**File**: `management-ui/frontend/src/components/backup/BackupScheduleConfig.tsx`

**Do**:
```typescript
import { useState, useEffect } from 'react';
import { Clock, Save } from 'lucide-react';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import { useBackupStore } from '../../store/backupStore';
import type { ScheduleFrequency, BackupDestination } from '../../types/backup';

export const BackupScheduleConfig: React.FC = () => {
  const { schedule, fetchSchedule, updateSchedule } = useBackupStore();

  const [enabled, setEnabled] = useState(false);
  const [frequency, setFrequency] = useState<ScheduleFrequency>('daily');
  const [hour, setHour] = useState(2);
  const [dayOfWeek, setDayOfWeek] = useState(0);
  const [destination, setDestination] = useState<BackupDestination>('local');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    fetchSchedule();
  }, [fetchSchedule]);

  useEffect(() => {
    if (schedule) {
      setEnabled(schedule.enabled);
      setFrequency(schedule.frequency);
      setHour(schedule.hour);
      setDayOfWeek(schedule.day_of_week);
      setDestination(schedule.destination);
    }
  }, [schedule]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await updateSchedule({
        enabled,
        frequency,
        hour,
        day_of_week: dayOfWeek,
        destination,
        services: [],
      });
    } catch {
      // Error handled by store
    } finally {
      setIsSaving(false);
    }
  };

  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

  return (
    <Card>
      <h4 className="font-semibold text-white mb-4 flex items-center gap-2">
        <Clock className="w-5 h-5 text-purple-400" />
        Backup Schedule
      </h4>

      <div className="space-y-4">
        {/* Enable Toggle */}
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
            className="w-5 h-5 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500"
          />
          <span className="text-white">Enable scheduled backups</span>
        </label>

        {enabled && (
          <>
            {/* Frequency */}
            <div>
              <label className="block text-sm text-gray-400 mb-2">Frequency</label>
              <select
                value={frequency}
                onChange={(e) => setFrequency(e.target.value as ScheduleFrequency)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-blue-500 focus:outline-none"
              >
                <option value="hourly">Hourly</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
              </select>
            </div>

            {/* Time (for daily/weekly) */}
            {(frequency === 'daily' || frequency === 'weekly') && (
              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  Time (24-hour format)
                </label>
                <select
                  value={hour}
                  onChange={(e) => setHour(parseInt(e.target.value))}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-blue-500 focus:outline-none"
                >
                  {Array.from({ length: 24 }, (_, i) => (
                    <option key={i} value={i}>
                      {i.toString().padStart(2, '0')}:00
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Day of week (for weekly) */}
            {frequency === 'weekly' && (
              <div>
                <label className="block text-sm text-gray-400 mb-2">Day of Week</label>
                <select
                  value={dayOfWeek}
                  onChange={(e) => setDayOfWeek(parseInt(e.target.value))}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-blue-500 focus:outline-none"
                >
                  {days.map((day, i) => (
                    <option key={day} value={i}>
                      {day}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Destination */}
            <div>
              <label className="block text-sm text-gray-400 mb-2">Destination</label>
              <div className="flex gap-3">
                <button
                  onClick={() => setDestination('local')}
                  className={`px-4 py-2 rounded-lg border transition-colors ${
                    destination === 'local'
                      ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                      : 'border-gray-600 text-gray-400 hover:border-gray-500'
                  }`}
                >
                  Local
                </button>
                <button
                  onClick={() => setDestination('s3')}
                  className={`px-4 py-2 rounded-lg border transition-colors ${
                    destination === 's3'
                      ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                      : 'border-gray-600 text-gray-400 hover:border-gray-500'
                  }`}
                >
                  S3 / MinIO
                </button>
              </div>
            </div>
          </>
        )}

        <Button
          variant="primary"
          onClick={handleSave}
          disabled={isSaving}
          isLoading={isSaving}
        >
          <Save className="w-4 h-4 mr-2" />
          Save Schedule
        </Button>
      </div>
    </Card>
  );
};
```

**Verify**: TypeScript compiler will check on build

---

### Task 14: Create Component Barrel Export

**Why**: Clean imports for backup components.

**File**: `management-ui/frontend/src/components/backup/index.ts`

**Do**:
```typescript
export { VolumeBackupManager } from './VolumeBackupManager';
export { BackupScheduleConfig } from './BackupScheduleConfig';
```

**Verify**: TypeScript compiler will check on build

---

### Task 15: Create Backups Page

**Why**: Dedicated page for backup management.

**Mirror**: `frontend/src/pages/Configuration.tsx`

**File**: `management-ui/frontend/src/pages/Backups.tsx`

**Do**:
```typescript
import { HardDrive } from 'lucide-react';
import { VolumeBackupManager, BackupScheduleConfig } from '../components/backup';

export const Backups: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-white flex items-center gap-3">
          <HardDrive className="w-7 h-7 text-slate-400" />
          Backup & Restore
        </h2>
        <p className="text-slate-400 mt-1">
          Manage Docker volume backups and restore points
        </p>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <VolumeBackupManager />
        </div>
        <div>
          <BackupScheduleConfig />
        </div>
      </div>
    </div>
  );
};
```

**Verify**: TypeScript compiler will check on build

---

### Task 16: Update App.tsx with Backup Route

**Why**: Add routing for the backup page.

**Mirror**: `frontend/src/App.tsx:64` (existing route pattern)

**File**: `management-ui/frontend/src/App.tsx`

**Do**:
Add import at top:
```typescript
import { Backups } from './pages/Backups';
```

Add route inside MainLayout routes (after `/logs`):
```typescript
<Route path="/backups" element={<Backups />} />
```

**Don't**:
- Don't remove existing routes

**Verify**: `npm run build` in frontend directory

---

### Task 17: Update Sidebar with Backup Navigation

**Why**: Add navigation link to backups page.

**Mirror**: `frontend/src/components/layout/Sidebar.tsx` (existing nav items)

**File**: `management-ui/frontend/src/components/layout/Sidebar.tsx`

**Do**:
Add import for HardDrive icon:
```typescript
import { ..., HardDrive } from 'lucide-react';
```

Add nav item after the Logs item in the navigation array:
```typescript
{ icon: HardDrive, label: 'Backups', path: '/backups' },
```

**Don't**:
- Don't change the order of existing nav items (add at end or logical position)

**Verify**: Visual inspection after running dev server

---

## Validation Strategy

### Automated Checks
- [ ] `cd /opt/local-ai-packaged/management-ui/backend && pip install -r requirements.txt` - Dependencies installed
- [ ] `cd /opt/local-ai-packaged/management-ui/backend && python -c "from app.api.routes import api_router; print('OK')"` - Backend imports work
- [ ] `cd /opt/local-ai-packaged/management-ui/frontend && npm run build` - Frontend builds without errors
- [ ] `cd /opt/local-ai-packaged/management-ui/frontend && npm run lint` - No lint errors

### New Tests to Write
| Test File | Test Case | What It Validates |
|-----------|-----------|-------------------|
| N/A (manual testing) | Create local backup | Backup creates successfully |
| N/A (manual testing) | Restore from backup | Data is restored correctly |
| N/A (manual testing) | S3 upload | Backup uploads to MinIO |
| N/A (manual testing) | Schedule configuration | Schedule saves and loads |

### Manual Validation
```bash
# Start the management UI backend
cd /opt/local-ai-packaged/management-ui/backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8001

# Test backup API endpoints
curl -X GET http://localhost:8001/api/backup/volumes -H "Authorization: Bearer <token>"
curl -X POST http://localhost:8001/api/backup -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"destination": "local"}'

# Start frontend
cd /opt/local-ai-packaged/management-ui/frontend
npm run dev

# Navigate to http://localhost:3000/backups
```

### Edge Cases to Test
- [ ] Backup with no running containers (should work on volumes)
- [ ] Backup with PostgreSQL running (should use pg_dump)
- [ ] Restore to empty volume (volume should be created)
- [ ] S3 connection with wrong credentials (should show clear error)
- [ ] Large volume backup (>1GB) - verify progress updates
- [ ] Cancel backup in progress (background task continues)
- [ ] Delete backup while restore in progress (should fail gracefully)

### Regression Check
- [ ] Existing config backups still work (`/config/backups` endpoint)
- [ ] Service start/stop still works
- [ ] Log streaming still works
- [ ] Configuration editor still saves properly

## Risks

1. **Long-running backups may timeout**: FastAPI background tasks should handle this, but very large volumes may need chunked processing
2. **PostgreSQL backup requires container running**: pg_dump fails if container is stopped
3. **S3 credentials stored in settings**: Consider adding encryption or vault integration later
4. **Volume size calculation is slow**: Uses `docker run` which has overhead
5. **Concurrent backups not prevented**: Could add job queue with locking

## Implementation Notes

1. **boto3 vs minio SDK**: Using boto3 as it's more versatile and widely supported
2. **Scheduler simplicity**: Using threading instead of APScheduler to minimize dependencies
3. **Job tracking in memory**: For MVP, jobs are tracked in memory. Consider Redis for production persistence
4. **No encryption**: Backup encryption (GPG) is out of scope for v1

---

## Plan File Info

**Created**: 2025-12-27
**Type**: Implementation Plan
**Status**: Ready for implementation
**Save to**: `.agents/plans/04-backup-system.plan.md`

To implement: `/implement .agents/plans/04-backup-system.plan.md`
