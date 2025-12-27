import docker
from docker.errors import NotFound, APIError
from typing import Dict, Optional, Generator
from datetime import datetime
import threading
import queue
import time


class MetricsCollector:
    """Collects container metrics using Docker stats API."""

    def __init__(self, docker_client: docker.DockerClient):
        self.client = docker_client

    def get_container_stats(self, container_id: str) -> Optional[Dict]:
        """Get a single stats snapshot for a container."""
        try:
            container = self.client.containers.get(container_id)
            # stream=False returns single stats dict
            stats = container.stats(stream=False)
            return self._parse_stats(container.name, container_id, stats)
        except (NotFound, APIError):
            return None

    def stream_container_stats(
        self,
        container_id: str,
        interval: float = 2.0
    ) -> Generator[Dict, None, None]:
        """Stream stats for a container with calculated deltas."""
        try:
            container = self.client.containers.get(container_id)
            prev_stats = None
            prev_time = None

            for stats in container.stats(stream=True, decode=True):
                current_time = datetime.utcnow()
                parsed = self._parse_stats_with_delta(
                    container.name,
                    container_id,
                    stats,
                    prev_stats,
                    prev_time,
                    current_time
                )
                if parsed:
                    yield parsed
                prev_stats = stats
                prev_time = current_time
                time.sleep(interval)

        except (NotFound, APIError):
            return

    def get_all_container_stats(self, project: str = "localai") -> Dict[str, Dict]:
        """Get stats for all containers in a project."""
        results = {}
        containers = self.client.containers.list(
            filters={"label": f"com.docker.compose.project={project}"}
        )

        for container in containers:
            try:
                stats = container.stats(stream=False)
                service_name = container.labels.get("com.docker.compose.service", container.name)
                parsed = self._parse_stats(service_name, container.short_id, stats)
                if parsed:
                    results[service_name] = parsed
            except (NotFound, APIError):
                continue

        return results

    def _parse_stats(
        self,
        service_name: str,
        container_id: str,
        stats: Dict
    ) -> Optional[Dict]:
        """Parse raw Docker stats into our format."""
        try:
            # CPU calculation
            cpu_stats = stats.get("cpu_stats", {})
            precpu_stats = stats.get("precpu_stats", {})

            cpu_usage = cpu_stats.get("cpu_usage", {})
            precpu_usage = precpu_stats.get("cpu_usage", {})

            cpu_delta = cpu_usage.get("total_usage", 0) - precpu_usage.get("total_usage", 0)
            system_delta = cpu_stats.get("system_cpu_usage", 0) - precpu_stats.get("system_cpu_usage", 0)
            num_cpus = cpu_stats.get("online_cpus") or len(cpu_usage.get("percpu_usage", [1]))

            cpu_percent = 0.0
            if system_delta > 0 and cpu_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0

            # Memory calculation
            memory_stats = stats.get("memory_stats", {})
            memory_usage = memory_stats.get("usage", 0)
            # Subtract cache for actual usage
            cache = memory_stats.get("stats", {}).get("cache", 0)
            memory_usage = max(0, memory_usage - cache)
            memory_limit = memory_stats.get("limit", 1)
            memory_percent = (memory_usage / memory_limit) * 100 if memory_limit > 0 else 0

            # Network calculation
            networks = stats.get("networks", {})
            rx_bytes = sum(n.get("rx_bytes", 0) for n in networks.values())
            tx_bytes = sum(n.get("tx_bytes", 0) for n in networks.values())

            return {
                "service_name": service_name,
                "container_id": container_id,
                "timestamp": datetime.utcnow().isoformat(),
                "cpu_percent": round(cpu_percent, 2),
                "memory_usage": memory_usage,
                "memory_limit": memory_limit,
                "memory_percent": round(memory_percent, 2),
                "network_rx_bytes": rx_bytes,
                "network_tx_bytes": tx_bytes,
                "network_rx_rate": 0.0,  # Need delta for rate
                "network_tx_rate": 0.0,
            }
        except (KeyError, TypeError, ZeroDivisionError):
            return None

    def _parse_stats_with_delta(
        self,
        service_name: str,
        container_id: str,
        stats: Dict,
        prev_stats: Optional[Dict],
        prev_time: Optional[datetime],
        current_time: datetime
    ) -> Optional[Dict]:
        """Parse stats with network rate calculation from delta."""
        base = self._parse_stats(service_name, container_id, stats)
        if not base:
            return None

        # Calculate network rates if we have previous stats
        if prev_stats and prev_time:
            time_delta = (current_time - prev_time).total_seconds()
            if time_delta > 0:
                prev_networks = prev_stats.get("networks", {})
                curr_networks = stats.get("networks", {})

                prev_rx = sum(n.get("rx_bytes", 0) for n in prev_networks.values())
                prev_tx = sum(n.get("tx_bytes", 0) for n in prev_networks.values())
                curr_rx = sum(n.get("rx_bytes", 0) for n in curr_networks.values())
                curr_tx = sum(n.get("tx_bytes", 0) for n in curr_networks.values())

                base["network_rx_rate"] = round((curr_rx - prev_rx) / time_delta, 2)
                base["network_tx_rate"] = round((curr_tx - prev_tx) / time_delta, 2)

        return base


class AsyncMetricsCollector:
    """Async wrapper for metrics collection using threading."""

    def __init__(self, docker_client: docker.DockerClient, project: str = "localai"):
        self.collector = MetricsCollector(docker_client)
        self.project = project
        self._metrics_queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self, interval: float = 2.0):
        """Start background metrics collection."""
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._collect_loop,
            args=(interval,),
            daemon=True
        )
        self._thread.start()

    def stop(self):
        """Stop background metrics collection."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)

    def get_latest(self) -> Optional[Dict[str, Dict]]:
        """Get the latest metrics from the queue."""
        latest = None
        try:
            while True:
                latest = self._metrics_queue.get_nowait()
        except queue.Empty:
            pass
        return latest

    def _collect_loop(self, interval: float):
        """Background collection loop."""
        while not self._stop_event.is_set():
            try:
                metrics = self.collector.get_all_container_stats(self.project)
                # Clear queue and put new metrics
                try:
                    while True:
                        self._metrics_queue.get_nowait()
                except queue.Empty:
                    pass
                self._metrics_queue.put(metrics)
            except Exception:
                pass
            time.sleep(interval)
