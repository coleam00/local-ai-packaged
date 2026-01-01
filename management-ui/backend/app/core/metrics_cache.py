"""
Background metrics caching service.

Collects Docker container metrics periodically and caches them
so the Health dashboard can display data immediately.
"""
import asyncio
from datetime import datetime
from typing import Dict, Optional, Any
import docker
from docker.errors import DockerException


class MetricsCache:
    """Singleton cache for container metrics."""

    _instance: Optional['MetricsCache'] = None
    _lock = asyncio.Lock()

    def __init__(self):
        self._metrics: Dict[str, Any] = {}
        self._timestamp: Optional[datetime] = None
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._interval = 30  # seconds
        self._project = "localai"

    @classmethod
    def get_instance(cls) -> 'MetricsCache':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def metrics(self) -> Dict[str, Any]:
        return self._metrics.copy()

    @property
    def timestamp(self) -> Optional[datetime]:
        return self._timestamp

    @property
    def has_data(self) -> bool:
        return bool(self._metrics)

    async def start(self):
        """Start the background collection task."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._collection_loop())
        print("METRICS CACHE: Background collection started", flush=True)

    async def stop(self):
        """Stop the background collection task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("METRICS CACHE: Background collection stopped", flush=True)

    async def _collection_loop(self):
        """Main collection loop."""
        while self._running:
            try:
                await self._collect_metrics()
            except Exception as e:
                print(f"METRICS CACHE ERROR: {e}", flush=True)

            await asyncio.sleep(self._interval)

    async def _collect_metrics(self):
        """Collect metrics from all containers."""
        try:
            # Run blocking Docker calls in thread pool
            metrics = await asyncio.to_thread(self._collect_sync)

            async with self._lock:
                self._metrics = metrics
                self._timestamp = datetime.utcnow()

        except DockerException as e:
            print(f"METRICS CACHE: Docker error - {e}", flush=True)

    def _collect_sync(self) -> Dict[str, Any]:
        """Synchronous metrics collection (runs in thread)."""
        client = docker.from_env()
        results = {}

        containers = client.containers.list(
            filters={"label": f"com.docker.compose.project={self._project}"}
        )

        for container in containers:
            try:
                stats = container.stats(stream=False)
                service_name = container.labels.get(
                    "com.docker.compose.service",
                    container.name
                )
                parsed = self._parse_stats(service_name, container.short_id, stats)
                if parsed:
                    results[service_name] = parsed
            except Exception:
                continue

        return results

    def _parse_stats(self, service_name: str, container_id: str, stats: Dict) -> Optional[Dict]:
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
                "network_rx_rate": 0.0,
                "network_tx_rate": 0.0,
            }
        except (KeyError, TypeError, ZeroDivisionError):
            return None


# Convenience function to get the singleton
def get_metrics_cache() -> MetricsCache:
    return MetricsCache.get_instance()
