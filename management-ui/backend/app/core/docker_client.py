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
