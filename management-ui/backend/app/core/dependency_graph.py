from typing import Dict, List, Set, Optional
from dataclasses import dataclass
from .compose_parser import ComposeParser, ServiceDefinition
from .service_dependencies import (
    SERVICE_CONFIGS, SERVICE_GROUPS as CENTRALIZED_GROUPS,
    get_required_for_selection, validate_selection
)

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

    def get_service_config(self, service_name: str):
        """Get centralized config for a service."""
        return SERVICE_CONFIGS.get(service_name)

    def get_enhanced_service_info(self, service_name: str, profile: str) -> Optional[Dict]:
        """Get service info combining docker-compose and centralized config."""
        compose_def = self.services.get(service_name)
        central_config = SERVICE_CONFIGS.get(service_name)

        if not compose_def:
            return None

        return {
            "name": service_name,
            "display_name": central_config.display_name if central_config else service_name,
            "description": central_config.description if central_config else f"From {compose_def.compose_file}",
            "group": central_config.group if central_config else self.get_service_group(service_name),
            "dependencies": list(central_config.dependencies) if central_config else list(compose_def.depends_on.keys()),
            "required": central_config.required if central_config else False,
            "default_enabled": central_config.default_enabled if central_config else True,
            "profiles": central_config.profiles if central_config else compose_def.profiles,
            "category": central_config.category if central_config else "optional",
            "available_for_profile": (
                not central_config.profiles or
                profile in central_config.profiles or
                profile == "none"
            ) if central_config else True
        }

    def validate_service_selection(self, selected: List[str], profile: str) -> Dict:
        """Validate a service selection with the centralized config."""
        return validate_selection(selected, profile)
