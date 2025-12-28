import subprocess
import shutil
import secrets
import asyncio
from pathlib import Path
from typing import List, Optional
from ..core.docker_client import DockerClient
from ..core.env_manager import EnvManager
from ..core.secret_generator import generate_missing_secrets
from ..core.compose_parser import ComposeParser
from ..core.dependency_graph import DependencyGraph
from ..schemas.setup import (
    SetupStatusResponse, SetupConfigRequest, SetupProgressResponse,
    SetupStepResult, ServiceSelectionInfo, ServiceSelectionValidation
)
from ..core.service_dependencies import SERVICE_CONFIGS, SERVICE_GROUPS, validate_selection
from ..core.port_scanner import PortScanner, get_all_default_ports
from typing import Dict


def _format_docker_error(raw_output: str) -> str:
    """Format docker compose error output for readability."""
    lines = raw_output.strip().split('\n') if raw_output else []

    warnings = []
    errors = []
    status_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Parse docker compose log format: time="..." level=... msg="..."
        if 'level=warning' in line:
            # Extract the message
            if 'msg="' in line:
                msg_start = line.index('msg="') + 5
                msg_end = line.rindex('"')
                warnings.append(line[msg_start:msg_end])
        elif 'level=error' in line or 'Error' in line or 'error' in line.lower():
            # Clean up error lines
            if 'msg="' in line:
                msg_start = line.index('msg="') + 5
                msg_end = line.rindex('"')
                errors.append(line[msg_start:msg_end])
            else:
                errors.append(line)
        elif any(keyword in line for keyword in ['Creating', 'Created', 'Starting', 'Started', 'Waiting', 'failed', 'unhealthy']):
            status_lines.append(line)

    # Build formatted output
    parts = []

    if errors:
        parts.append("ERRORS:")
        for err in errors:
            parts.append(f"  • {err}")

    if warnings:
        # Deduplicate warnings
        unique_warnings = list(dict.fromkeys(warnings))
        parts.append("\nWARNINGS:")
        for warn in unique_warnings:
            parts.append(f"  • {warn}")

    if status_lines:
        # Show last few status lines for context
        parts.append("\nSTATUS:")
        for status in status_lines[-10:]:
            parts.append(f"  {status}")

    return '\n'.join(parts) if parts else raw_output


class SetupService:
    """Handles initial setup and stack orchestration."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.docker_client = DockerClient(base_path=str(base_path))
        self.env_manager = EnvManager(str(base_path))

    def get_status(self) -> SetupStatusResponse:
        """Check current setup status."""
        has_env = self.env_manager.env_file_exists()
        supabase_cloned = (self.base_path / "supabase" / "docker").exists()

        # Check for missing secrets
        missing_secrets: List[str] = []
        if has_env:
            env = self.env_manager.load()
            errors = self.env_manager.validate(env)
            missing_secrets = [
                e["variable"] for e in errors
                if e["error"] in ("required", "placeholder")
            ]

        # Count running services
        try:
            containers = self.docker_client.list_containers()
            running = sum(1 for c in containers if c.get("status") == "running")
        except Exception:
            running = 0

        setup_required = not has_env or len(missing_secrets) > 0 or not supabase_cloned

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
            setup_required=setup_required,
            has_env_file=has_env,
            has_secrets=len(missing_secrets) == 0,
            supabase_cloned=supabase_cloned,
            services_running=running,
            stack_running=stack_running,
            missing_secrets=missing_secrets
        )

    def get_available_services(self, profile: str = "cpu") -> List[ServiceSelectionInfo]:
        """Get list of services available for selection with enhanced info."""
        try:
            parser = ComposeParser(str(self.base_path))
            graph = DependencyGraph(parser)
        except Exception:
            return []

        services = []
        for name, svc_def in parser.services.items():
            # Skip init containers
            if "import" in name:
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

    def validate_service_selection(self, selected: List[str], profile: str) -> dict:
        """Validate a service selection."""
        return validate_selection(selected, profile)

    def check_port_availability(self, enabled_services: List[str] = None) -> dict:
        """
        Check port availability for selected services.
        Returns scan results with conflicts and suggestions.
        """
        scanner = PortScanner()
        scanner.load_docker_ports(self.docker_client)

        # Get ports to check
        all_ports = get_all_default_ports()

        # Filter to enabled services if specified
        if enabled_services:
            all_ports = {
                name: ports for name, ports in all_ports.items()
                if name in enabled_services
            }

        results = []
        total_ports = 0
        conflicts = 0

        for service_name, default_ports in all_ports.items():
            if not default_ports:
                continue

            config = SERVICE_CONFIGS.get(service_name)
            if not config:
                continue

            result = scanner.scan_service_ports(
                service_name=service_name,
                display_name=config.display_name,
                default_ports=default_ports
            )
            results.append({
                "service_name": result.service_name,
                "display_name": result.display_name,
                "ports": {
                    name: {
                        "port": ps.port,
                        "available": ps.available,
                        "used_by": ps.used_by
                    }
                    for name, ps in result.ports.items()
                },
                "all_available": result.all_available,
                "suggested_ports": result.suggested_ports
            })

            total_ports += len(default_ports)
            if not result.all_available:
                conflicts += sum(1 for ps in result.ports.values() if not ps.available)

        return {
            "has_conflicts": conflicts > 0,
            "services": results,
            "total_ports_checked": total_ports,
            "conflicts_count": conflicts
        }

    def validate_port_configuration(self, port_config: Dict[str, Dict[str, int]]) -> dict:
        """
        Validate user's custom port configuration.
        Check that all specified ports are available.
        """
        scanner = PortScanner()
        scanner.load_docker_ports(self.docker_client)

        errors = []
        warnings = []

        # Check each configured port
        all_ports = []
        for service_name, ports in port_config.items():
            for port_name, port in ports.items():
                # Check availability
                available, used_by = scanner.is_port_available(port)
                if not available:
                    errors.append(f"Port {port} ({service_name}.{port_name}) is in use by {used_by}")

                # Check for duplicates
                if port in all_ports:
                    errors.append(f"Port {port} is configured multiple times")
                all_ports.append(port)

                # Check port range
                if port < 1024:
                    warnings.append(f"Port {port} requires root/admin privileges")
                if port > 65535:
                    errors.append(f"Port {port} is invalid (must be 1-65535)")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    def preflight_check(self) -> dict:
        """Check environment state before setup."""
        issues = []
        warnings = []
        can_proceed = True

        supabase_dir = self.base_path / "supabase"

        # Check supabase directory
        if supabase_dir.exists():
            git_dir = supabase_dir / ".git"
            if not git_dir.exists():
                issues.append({
                    "type": "supabase_not_git",
                    "message": "supabase/ folder exists but is not a git repository",
                    "fix": "delete_supabase"
                })
                can_proceed = False
            else:
                # Check if it's a valid supabase repo
                docker_dir = supabase_dir / "docker"
                if not docker_dir.exists():
                    warnings.append({
                        "type": "supabase_incomplete",
                        "message": "supabase/ repo exists but docker/ folder is missing",
                        "fix": "delete_supabase"
                    })

        # Check for existing Supabase database data (password mismatch issue)
        supabase_db_data = self.base_path / "supabase" / "docker" / "volumes" / "db" / "data"
        if supabase_db_data.exists() and any(supabase_db_data.iterdir()):
            warnings.append({
                "type": "supabase_db_exists",
                "message": "Supabase database data exists (may cause password mismatch)",
                "fix": "delete_supabase_db"
            })

        # Check for running containers
        try:
            containers = self.docker_client.list_containers()
            running = [c for c in containers if c.get("status") == "running"]
            if running:
                warnings.append({
                    "type": "containers_running",
                    "message": f"{len(running)} containers are currently running",
                    "fix": "stop_containers"
                })
        except Exception:
            pass

        # Check for existing volumes
        try:
            result = subprocess.run(
                ["docker", "volume", "ls", "-q", "--filter", "name=localai"],
                capture_output=True, text=True
            )
            volumes = [v for v in result.stdout.strip().split("\n") if v]
            if volumes:
                warnings.append({
                    "type": "volumes_exist",
                    "message": f"{len(volumes)} Docker volumes from previous install exist",
                    "fix": "delete_volumes"
                })
        except Exception:
            pass

        return {
            "can_proceed": can_proceed,
            "issues": issues,
            "warnings": warnings
        }

    def fix_preflight_issue(self, fix_type: str) -> dict:
        """Fix a preflight issue."""
        try:
            if fix_type == "delete_supabase":
                supabase_dir = self.base_path / "supabase"
                if supabase_dir.exists():
                    shutil.rmtree(supabase_dir)
                return {"success": True, "message": "Deleted supabase/ folder"}

            elif fix_type == "stop_containers":
                self.docker_client.compose_down(profile="cpu")
                return {"success": True, "message": "Stopped all containers"}

            elif fix_type == "delete_volumes":
                subprocess.run(
                    ["docker", "volume", "rm", "-f"] +
                    subprocess.run(
                        ["docker", "volume", "ls", "-q", "--filter", "name=localai"],
                        capture_output=True, text=True
                    ).stdout.strip().split(),
                    capture_output=True
                )
                return {"success": True, "message": "Deleted Docker volumes"}

            elif fix_type == "delete_supabase_db":
                supabase_db_data = self.base_path / "supabase" / "docker" / "volumes" / "db" / "data"
                if supabase_db_data.exists():
                    shutil.rmtree(supabase_db_data)
                return {"success": True, "message": "Deleted Supabase database data"}

            else:
                return {"success": False, "message": f"Unknown fix type: {fix_type}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def clone_supabase_repo(self) -> SetupStepResult:
        """Clone/update Supabase repository."""
        supabase_dir = self.base_path / "supabase"

        try:
            if not supabase_dir.exists():
                # Clone with sparse checkout
                subprocess.run([
                    "git", "clone", "--filter=blob:none", "--no-checkout",
                    "https://github.com/supabase/supabase.git",
                    str(supabase_dir)
                ], check=True, capture_output=True)

                subprocess.run(
                    ["git", "sparse-checkout", "init", "--cone"],
                    cwd=supabase_dir, check=True, capture_output=True
                )
                subprocess.run(
                    ["git", "sparse-checkout", "set", "docker"],
                    cwd=supabase_dir, check=True, capture_output=True
                )
                subprocess.run(
                    ["git", "checkout", "master"],
                    cwd=supabase_dir, check=True, capture_output=True
                )
            else:
                # Try to pull, but don't fail if it doesn't work
                result = subprocess.run(
                    ["git", "pull"],
                    cwd=supabase_dir, capture_output=True, text=True
                )
                if result.returncode != 0:
                    # Reset to origin/master if pull fails
                    subprocess.run(
                        ["git", "fetch", "origin"],
                        cwd=supabase_dir, capture_output=True
                    )
                    subprocess.run(
                        ["git", "reset", "--hard", "origin/master"],
                        cwd=supabase_dir, capture_output=True
                    )

            return SetupStepResult(
                step="clone_supabase",
                status="completed",
                message="Supabase repository ready"
            )
        except Exception as e:
            return SetupStepResult(
                step="clone_supabase",
                status="failed",
                error=str(e)
            )

    def prepare_env_file(self, config: SetupConfigRequest) -> SetupStepResult:
        """Prepare .env file with secrets, hostnames, and port configuration."""
        try:
            # Start with existing or default config
            if self.env_manager.env_file_exists():
                env = self.env_manager.load()
            else:
                # Load from example if exists
                if self.env_manager.env_example.exists():
                    env = {}
                    with open(self.env_manager.env_example) as f:
                        for line in f:
                            if "=" in line and not line.strip().startswith("#"):
                                key, _, val = line.partition("=")
                                env[key.strip()] = val.strip()
                else:
                    env = {}

            # Apply provided secrets
            env.update(config.secrets)

            # Generate any missing secrets
            missing = generate_missing_secrets(env)
            env.update(missing)

            # Apply hostnames if public environment
            if config.environment.value == "public":
                env.update(config.hostnames)

            # Apply port overrides (only for private environment)
            if config.port_overrides and config.environment.value == "private":
                port_env_mapping = {
                    ("flowise", "http"): "FLOWISE_PORT",
                    ("open-webui", "http"): "OPENWEBUI_PORT",
                    ("n8n", "http"): "N8N_PORT",
                    ("qdrant", "http"): "QDRANT_HTTP_PORT",
                    ("qdrant", "grpc"): "QDRANT_GRPC_PORT",
                    ("neo4j", "https"): "NEO4J_HTTPS_PORT",
                    ("neo4j", "http"): "NEO4J_HTTP_PORT",
                    ("neo4j", "bolt"): "NEO4J_BOLT_PORT",
                    ("langfuse-web", "http"): "LANGFUSE_PORT",
                    ("langfuse-worker", "http"): "LANGFUSE_WORKER_PORT",
                    ("clickhouse", "http"): "CLICKHOUSE_HTTP_PORT",
                    ("clickhouse", "native"): "CLICKHOUSE_NATIVE_PORT",
                    ("clickhouse", "mysql"): "CLICKHOUSE_MYSQL_PORT",
                    ("minio", "api"): "MINIO_API_PORT",
                    ("minio", "console"): "MINIO_CONSOLE_PORT",
                    ("postgres", "db"): "LANGFUSE_POSTGRES_PORT",
                    ("redis", "db"): "REDIS_PORT",
                    ("searxng", "http"): "SEARXNG_PORT",
                    ("ollama-cpu", "http"): "OLLAMA_PORT",
                    ("ollama-gpu", "http"): "OLLAMA_PORT",
                    ("ollama-gpu-amd", "http"): "OLLAMA_PORT",
                }

                for service_name, ports in config.port_overrides.items():
                    for port_name, port_value in ports.items():
                        env_var = port_env_mapping.get((service_name, port_name))
                        if env_var:
                            env[env_var] = str(port_value)

            # Save
            self.env_manager.save(env, backup=True)

            return SetupStepResult(
                step="prepare_env",
                status="completed",
                message=f"Configuration saved with {len(missing)} generated secrets"
            )
        except Exception as e:
            return SetupStepResult(
                step="prepare_env",
                status="failed",
                error=str(e)
            )

    def generate_searxng_secret(self) -> SetupStepResult:
        """Generate SearXNG secret key."""
        try:
            settings_base = self.base_path / "searxng" / "settings-base.yml"
            settings_file = self.base_path / "searxng" / "settings.yml"

            if not settings_file.exists() and settings_base.exists():
                shutil.copy(settings_base, settings_file)

            if settings_file.exists():
                secret_key = secrets.token_hex(32)
                content = settings_file.read_text()
                if "ultrasecretkey" in content:
                    content = content.replace("ultrasecretkey", secret_key)
                    settings_file.write_text(content)

            return SetupStepResult(
                step="searxng_secret",
                status="completed",
                message="SearXNG secret generated"
            )
        except Exception as e:
            return SetupStepResult(
                step="searxng_secret",
                status="failed",
                error=str(e)
            )

    async def start_stack(
        self,
        profile: str,
        environment: str,
        enabled_services: Optional[List[str]] = None
    ) -> SetupStepResult:
        """Start the full stack."""
        try:
            # Stop existing containers first
            self.docker_client.compose_down(profile=profile)

            # Start Supabase
            supabase_cmd = [
                "docker", "compose", "-p", "localai",
                "-f", "supabase/docker/docker-compose.yml"
            ]
            if environment == "public":
                supabase_cmd.extend(["-f", "docker-compose.override.public.supabase.yml"])
            supabase_cmd.extend(["up", "-d"])

            result = subprocess.run(supabase_cmd, cwd=self.base_path, capture_output=True, text=True)
            if result.returncode != 0:
                raw_error = result.stderr or result.stdout or "Unknown error"
                formatted_error = _format_docker_error(raw_error)
                return SetupStepResult(
                    step="start_stack",
                    status="failed",
                    error=f"Failed to start Supabase:\n\n{formatted_error}"
                )

            # Wait for Supabase to be ready
            await asyncio.sleep(10)

            # Start local AI services
            result = self.docker_client.compose_up(
                services=enabled_services,
                profile=profile,
                environment=environment
            )

            if result.returncode == 0:
                return SetupStepResult(
                    step="start_stack",
                    status="completed",
                    message="Stack started successfully"
                )
            else:
                raw_error = result.stderr or result.stdout or "Unknown error"
                formatted_error = _format_docker_error(raw_error)
                return SetupStepResult(
                    step="start_stack",
                    status="failed",
                    error=f"Failed to start local AI services:\n\n{formatted_error}"
                )

        except Exception as e:
            return SetupStepResult(
                step="start_stack",
                status="failed",
                error=str(e)
            )

    async def run_full_setup(self, config: SetupConfigRequest) -> SetupProgressResponse:
        """Run the complete setup process."""
        steps: List[SetupStepResult] = []

        # Step 1: Clone Supabase
        result = await self.clone_supabase_repo()
        steps.append(result)
        if result.status == "failed":
            return SetupProgressResponse(
                status="failed",
                current_step="clone_supabase",
                steps=steps,
                error=result.error
            )

        # Step 2: Prepare environment
        result = self.prepare_env_file(config)
        steps.append(result)
        if result.status == "failed":
            return SetupProgressResponse(
                status="failed",
                current_step="prepare_env",
                steps=steps,
                error=result.error
            )

        # Step 3: SearXNG secret
        result = self.generate_searxng_secret()
        steps.append(result)
        # Non-fatal if fails

        # Step 4: Start stack
        result = await self.start_stack(
            profile=config.profile.value,
            environment=config.environment.value,
            enabled_services=config.enabled_services if config.enabled_services else None
        )
        steps.append(result)

        if result.status == "failed":
            return SetupProgressResponse(
                status="failed",
                current_step="start_stack",
                steps=steps,
                error=result.error
            )

        return SetupProgressResponse(
            status="completed",
            current_step="done",
            steps=steps,
            message="Setup completed successfully!"
        )
