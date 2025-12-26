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
