from typing import List, Dict, Optional, Tuple
from ..core.docker_client import DockerClient
from ..core.compose_parser import ComposeParser
from ..core.dependency_graph import DependencyGraph
from ..schemas.service import (
    ServiceInfo, ServiceStatus, HealthStatus,
    ServiceDetailResponse, ServiceActionResponse, DependencyWarning
)

class DockerService:
    """Service layer for Docker operations."""

    def __init__(
        self,
        docker_client: DockerClient,
        parser: ComposeParser,
        graph: DependencyGraph
    ):
        self.docker = docker_client
        self.parser = parser
        self.graph = graph

    def list_services(self) -> List[ServiceInfo]:
        """List all services with their current status."""
        # Get running containers
        containers = self.docker.list_containers(all=True)
        container_map = {c["service"]: c for c in containers if c.get("service")}

        services = []
        for name, svc_def in self.parser.services.items():
            container = container_map.get(name)

            if container:
                status = self._map_container_status(container["status"])
                health = self._map_health_status(container["health"])
                image = container.get("image")
                container_id = container.get("id")
                ports = self._format_ports(container.get("ports", {}))
            else:
                status = ServiceStatus.NOT_CREATED
                health = HealthStatus.NONE
                image = svc_def.image
                container_id = None
                ports = svc_def.ports

            services.append(ServiceInfo(
                name=name,
                status=status,
                health=health,
                image=image,
                container_id=container_id,
                ports=ports,
                group=self.graph.get_service_group(name),
                compose_file=svc_def.compose_file,
                profiles=svc_def.profiles,
                has_healthcheck=svc_def.has_healthcheck,
                depends_on=svc_def.depends_on
            ))

        return sorted(services, key=lambda s: (s.group, s.name))

    def get_service(self, name: str) -> Optional[ServiceDetailResponse]:
        """Get detailed info about a specific service."""
        svc_def = self.parser.get_service(name)
        if not svc_def:
            return None

        container = self.docker.get_container(name)

        if container:
            status = self._map_container_status(container["status"])
            health = self._map_health_status(container["health"])
            image = container.get("image")
            container_id = container.get("id")
            ports = self._format_ports(container.get("ports", {}))
            created = container.get("created")
        else:
            status = ServiceStatus.NOT_CREATED
            health = HealthStatus.NONE
            image = svc_def.image
            container_id = None
            ports = svc_def.ports
            created = None

        return ServiceDetailResponse(
            name=name,
            status=status,
            health=health,
            image=image,
            container_id=container_id,
            ports=ports,
            group=self.graph.get_service_group(name),
            compose_file=svc_def.compose_file,
            profiles=svc_def.profiles,
            has_healthcheck=svc_def.has_healthcheck,
            depends_on=svc_def.depends_on,
            environment=svc_def.environment,
            created=created,
            dependents=list(self.graph.get_dependents(name)),
            dependencies=list(self.graph.get_dependencies(name))
        )

    def start_service(
        self,
        name: str,
        profile: Optional[str] = None,
        environment: str = "private"
    ) -> ServiceActionResponse:
        """Start a service and its dependencies."""
        svc_def = self.parser.get_service(name)
        if not svc_def:
            return ServiceActionResponse(
                success=False,
                message=f"Service '{name}' not found",
                service=name,
                action="start"
            )

        # Check if service requires a specific profile
        if svc_def.profiles and profile not in svc_def.profiles:
            if not profile:
                profile = svc_def.profiles[0]

        try:
            result = self.docker.compose_up(
                services=[name],
                profile=profile,
                environment=environment
            )

            if result.returncode == 0:
                return ServiceActionResponse(
                    success=True,
                    message=f"Service '{name}' started successfully",
                    service=name,
                    action="start",
                    output=result.stdout
                )
            else:
                return ServiceActionResponse(
                    success=False,
                    message=f"Failed to start service '{name}'",
                    service=name,
                    action="start",
                    error=result.stderr
                )
        except Exception as e:
            return ServiceActionResponse(
                success=False,
                message=str(e),
                service=name,
                action="start",
                error=str(e)
            )

    def stop_service(
        self,
        name: str,
        force: bool = False,
        profile: Optional[str] = None
    ) -> Tuple[ServiceActionResponse, Optional[DependencyWarning]]:
        """Stop a service, with warning about dependents."""
        svc_def = self.parser.get_service(name)
        if not svc_def:
            return ServiceActionResponse(
                success=False,
                message=f"Service '{name}' not found",
                service=name,
                action="stop"
            ), None

        # Check for dependents
        warning = None
        dependents = self.graph.get_dependents(name)
        if dependents and not force:
            warning = DependencyWarning(
                service=name,
                dependents=list(dependents),
                message=f"Stopping {name} will affect: {', '.join(sorted(dependents))}"
            )
            # Still proceed but return warning

        try:
            result = self.docker.compose_down(
                services=[name],
                profile=profile
            )

            if result.returncode == 0:
                return ServiceActionResponse(
                    success=True,
                    message=f"Service '{name}' stopped successfully",
                    service=name,
                    action="stop",
                    output=result.stdout
                ), warning
            else:
                return ServiceActionResponse(
                    success=False,
                    message=f"Failed to stop service '{name}'",
                    service=name,
                    action="stop",
                    error=result.stderr
                ), warning
        except Exception as e:
            return ServiceActionResponse(
                success=False,
                message=str(e),
                service=name,
                action="stop",
                error=str(e)
            ), warning

    def restart_service(
        self,
        name: str,
        profile: Optional[str] = None
    ) -> ServiceActionResponse:
        """Restart a service."""
        svc_def = self.parser.get_service(name)
        if not svc_def:
            return ServiceActionResponse(
                success=False,
                message=f"Service '{name}' not found",
                service=name,
                action="restart"
            )

        try:
            result = self.docker.compose_restart(
                services=[name],
                profile=profile
            )

            if result.returncode == 0:
                return ServiceActionResponse(
                    success=True,
                    message=f"Service '{name}' restarted successfully",
                    service=name,
                    action="restart",
                    output=result.stdout
                )
            else:
                return ServiceActionResponse(
                    success=False,
                    message=f"Failed to restart service '{name}'",
                    service=name,
                    action="restart",
                    error=result.stderr
                )
        except Exception as e:
            return ServiceActionResponse(
                success=False,
                message=str(e),
                service=name,
                action="restart",
                error=str(e)
            )

    def get_groups_with_status(self) -> Dict[str, Dict]:
        """Get service groups with running status."""
        groups = self.graph.get_groups()
        services = self.list_services()
        service_status = {s.name: s.status for s in services}

        result = {}
        for group_id, group_info in groups.items():
            running = sum(
                1 for s in group_info["services"]
                if service_status.get(s) == ServiceStatus.RUNNING
            )
            result[group_id] = {
                **group_info,
                "id": group_id,
                "running_count": running,
                "total_count": len(group_info["services"])
            }

        return result

    def _map_container_status(self, status: str) -> ServiceStatus:
        """Map Docker container status to ServiceStatus enum."""
        status_lower = status.lower()
        if status_lower == "running":
            return ServiceStatus.RUNNING
        elif status_lower in ("exited", "dead", "created"):
            return ServiceStatus.STOPPED
        elif status_lower == "restarting":
            return ServiceStatus.RESTARTING
        elif status_lower == "paused":
            return ServiceStatus.STOPPED
        else:
            return ServiceStatus.ERROR

    def _map_health_status(self, health: str) -> HealthStatus:
        """Map Docker health status to HealthStatus enum."""
        health_lower = health.lower() if health else "none"
        if health_lower == "healthy":
            return HealthStatus.HEALTHY
        elif health_lower == "unhealthy":
            return HealthStatus.UNHEALTHY
        elif health_lower == "starting":
            return HealthStatus.STARTING
        elif health_lower == "none":
            return HealthStatus.NONE
        else:
            return HealthStatus.UNKNOWN

    def _format_ports(self, ports: Dict) -> List[str]:
        """Format port mappings to string list."""
        result = []
        for container_port, host_bindings in ports.items():
            if host_bindings:
                for binding in host_bindings:
                    host_port = binding.get("HostPort", "")
                    host_ip = binding.get("HostIp", "0.0.0.0")
                    result.append(f"{host_ip}:{host_port}->{container_port}")
            else:
                result.append(container_port)
        return result
