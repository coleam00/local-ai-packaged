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
            # Skip init containers (except n8n-import which is needed for dependency tracking)
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

    def validate_service_selection(self, selected: List[str], profile: str) -> dict:
        """Validate a service selection."""
        return validate_selection(selected, profile)

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
                subprocess.run(
                    ["git", "pull"],
                    cwd=supabase_dir, check=True, capture_output=True
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
        """Prepare .env file with secrets and hostnames."""
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

            subprocess.run(supabase_cmd, cwd=self.base_path, check=True, capture_output=True)

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
                return SetupStepResult(
                    step="start_stack",
                    status="failed",
                    error=result.stderr
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
