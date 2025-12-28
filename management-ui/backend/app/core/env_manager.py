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

    def _parse_env_file(self, file_path: Path) -> Dict[str, str]:
        """Parse an env file, handling different line endings."""
        if not file_path.exists():
            return {}

        env = {}
        # Read with explicit encoding and normalize line endings
        content = file_path.read_text(encoding='utf-8', errors='replace')
        # Normalize line endings (handle Windows CRLF)
        content = content.replace('\r\n', '\n').replace('\r', '\n')

        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip()
                # Validate key: must be valid env var name (letters, digits, underscores, starting with letter/underscore)
                if key and self._is_valid_env_key(key):
                    env[key] = value
        return env

    def _is_valid_env_key(self, key: str) -> bool:
        """Check if a key is a valid environment variable name."""
        if not key:
            return False
        # Must start with letter or underscore
        if not (key[0].isalpha() or key[0] == '_'):
            return False
        # Rest must be alphanumeric or underscore
        return all(c.isalnum() or c == '_' for c in key)

    def load(self) -> Dict[str, str]:
        """Load current .env file."""
        return self._parse_env_file(self.env_file)

    def save(self, env: Dict[str, str], backup: bool = True) -> str:
        """Save .env file with optional backup. Returns backup path if created."""
        backup_path = None
        if backup and self.env_file.exists():
            backup_path = self._create_backup()

        # Try to preserve structure from example file
        lines = []
        written_keys = set()

        if self.env_example.exists():
            # Read with proper encoding and normalize line endings
            content = self.env_example.read_text(encoding='utf-8', errors='replace')
            content = content.replace('\r\n', '\n').replace('\r', '\n')

            for line in content.split('\n'):
                stripped = line.strip()
                if '=' in stripped and not stripped.startswith('#'):
                    key = stripped.split('=')[0].strip()
                    if key in env:
                        lines.append(f"{key}={env[key]}\n")
                        written_keys.add(key)
                    else:
                        lines.append(line + '\n')
                else:
                    lines.append(line + '\n')

        # Add any remaining new variables
        for key, value in env.items():
            if key not in written_keys:
                lines.append(f"{key}={value}\n")

        # Write with Unix line endings
        self.env_file.write_text(''.join(lines), encoding='utf-8', newline='\n')

        # Copy to Supabase directory
        self._sync_to_supabase()

        return backup_path or ""

    def _sync_to_supabase(self):
        """Merge root .env with supabase/docker/.env.example to create supabase/docker/.env"""
        supabase_dir = self.base_path / "supabase" / "docker"
        supabase_env = supabase_dir / ".env"
        supabase_example = supabase_dir / ".env.example"

        if not supabase_dir.exists() or not self.env_file.exists():
            return

        # Start with Supabase's .env.example as base (contains all required Supabase vars)
        supabase_vars = self._parse_env_file(supabase_example)

        # Overlay our root .env values (overrides Supabase defaults with our secrets)
        root_vars = self.load()
        supabase_vars.update(root_vars)

        # Write merged config to supabase/docker/.env with Unix line endings
        lines = [f"{key}={value}\n" for key, value in supabase_vars.items()]
        supabase_env.write_text(''.join(lines), encoding='utf-8', newline='\n')

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
