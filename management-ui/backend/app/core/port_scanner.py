"""
Port availability scanning utilities.
Checks for port conflicts with host services and Docker containers.
"""
import socket
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class PortStatus:
    """Status of a single port."""
    port: int
    available: bool
    used_by: Optional[str] = None  # Service name using this port


@dataclass
class PortScanResult:
    """Result of scanning ports for a service."""
    service_name: str
    display_name: str
    ports: Dict[str, PortStatus]  # port_name -> status
    all_available: bool
    suggested_ports: Dict[str, int]  # port_name -> suggested alternative


class PortScanner:
    """Scans for port availability on the host system."""

    def __init__(self, host: str = "127.0.0.1"):
        self.host = host
        self._docker_ports: Dict[int, str] = {}  # port -> container name

    def is_port_available(self, port: int) -> Tuple[bool, Optional[str]]:
        """
        Check if a port is available.
        Returns (available, used_by) tuple.
        """
        # Check host port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        try:
            result = sock.connect_ex((self.host, port))
            if result == 0:
                return False, "host service"
        except socket.error:
            pass
        finally:
            sock.close()

        # Check Docker container ports
        if port in self._docker_ports:
            return False, f"Docker: {self._docker_ports[port]}"

        return True, None

    def load_docker_ports(self, docker_client) -> None:
        """Load ports used by running Docker containers."""
        try:
            containers = docker_client.list_containers()
            for container in containers:
                if container.get("status") != "running":
                    continue
                ports = container.get("ports", {})
                if isinstance(ports, dict):
                    for port_key, bindings in ports.items():
                        if bindings:
                            for binding in bindings:
                                host_port = binding.get("HostPort")
                                if host_port:
                                    self._docker_ports[int(host_port)] = container.get("name", "unknown")
                elif isinstance(ports, list):
                    # Handle list format from some Docker API responses
                    for port_info in ports:
                        if isinstance(port_info, dict):
                            public_port = port_info.get("PublicPort")
                            if public_port:
                                self._docker_ports[int(public_port)] = container.get("name", "unknown")
        except Exception:
            pass  # Docker might not be available

    def find_available_port(self, start_port: int, max_attempts: int = 100) -> int:
        """Find next available port starting from start_port."""
        for offset in range(max_attempts):
            port = start_port + offset
            if port > 65535:
                break
            available, _ = self.is_port_available(port)
            if available:
                return port
        return start_port  # Return original if nothing found

    def scan_service_ports(
        self,
        service_name: str,
        display_name: str,
        default_ports: Dict[str, int]
    ) -> PortScanResult:
        """
        Scan ports for a service and suggest alternatives if needed.
        """
        ports = {}
        suggested = {}
        all_available = True

        for port_name, port in default_ports.items():
            available, used_by = self.is_port_available(port)
            ports[port_name] = PortStatus(
                port=port,
                available=available,
                used_by=used_by
            )

            if not available:
                all_available = False
                # Find alternative
                suggested[port_name] = self.find_available_port(port + 1)
            else:
                suggested[port_name] = port

        return PortScanResult(
            service_name=service_name,
            display_name=display_name,
            ports=ports,
            all_available=all_available,
            suggested_ports=suggested
        )


def get_all_default_ports() -> Dict[str, Dict[str, int]]:
    """Get all default ports from service configs."""
    from .service_dependencies import SERVICE_CONFIGS
    return {
        name: config.default_ports
        for name, config in SERVICE_CONFIGS.items()
        if config.default_ports
    }
