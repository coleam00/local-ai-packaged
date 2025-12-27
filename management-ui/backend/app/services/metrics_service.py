from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
import uuid
import json

from ..core.docker_client import DockerClient
from ..core.metrics_collector import MetricsCollector
from ..core.diagnostics import (
    analyze_metrics, analyze_logs, analyze_restart_pattern,
    should_recommend_restart, THRESHOLDS
)
from ..models.metrics import MetricsSnapshot as MetricsSnapshotModel
from ..models.metrics import HealthAlert as HealthAlertModel
from ..models.metrics import ServiceRestartEvent
from ..schemas.metrics import (
    ContainerMetrics, MetricsSnapshot, MetricsHistoryResponse,
    HealthAlert, AlertType, AlertSeverity, DiagnosticsResponse
)


class MetricsService:
    """Service for metrics collection, storage, and analysis."""

    def __init__(
        self,
        docker_client: DockerClient,
        db: Session
    ):
        self.docker = docker_client
        self.collector = MetricsCollector(docker_client.client)
        self.db = db
        self._aggregation_buffer: Dict[str, List[Dict]] = {}

    def get_current_metrics(self, service_name: str) -> Optional[ContainerMetrics]:
        """Get current metrics for a single service."""
        container = self.docker.get_container(service_name)
        if not container:
            return None

        stats = self.collector.get_container_stats(container["full_id"])
        if not stats:
            return None

        return ContainerMetrics(**stats)

    def get_all_current_metrics(self) -> List[ContainerMetrics]:
        """Get current metrics for all services."""
        stats = self.collector.get_all_container_stats(self.docker.project)
        return [ContainerMetrics(**s) for s in stats.values()]

    def get_metrics_history(
        self,
        service_name: str,
        hours: int = 24,
        granularity_seconds: int = 60
    ) -> MetricsHistoryResponse:
        """Get metrics history for a service."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        snapshots = self.db.query(MetricsSnapshotModel).filter(
            MetricsSnapshotModel.service_name == service_name,
            MetricsSnapshotModel.timestamp >= start_time,
            MetricsSnapshotModel.timestamp <= end_time
        ).order_by(MetricsSnapshotModel.timestamp).all()

        data_points = [
            MetricsSnapshot(
                service_name=s.service_name,
                timestamp=s.timestamp,
                cpu_avg=s.cpu_avg,
                cpu_max=s.cpu_max,
                memory_avg=s.memory_avg,
                memory_max=s.memory_max,
                network_rx_rate_avg=s.network_rx_rate_avg,
                network_tx_rate_avg=s.network_tx_rate_avg
            )
            for s in snapshots
        ]

        return MetricsHistoryResponse(
            service_name=service_name,
            start_time=start_time,
            end_time=end_time,
            data_points=data_points,
            granularity_seconds=granularity_seconds
        )

    def store_metrics_snapshot(self, metrics: ContainerMetrics):
        """Store a metrics snapshot (called periodically for aggregation)."""
        service = metrics.service_name

        # Add to buffer
        if service not in self._aggregation_buffer:
            self._aggregation_buffer[service] = []

        self._aggregation_buffer[service].append({
            "cpu": metrics.cpu_percent,
            "memory": metrics.memory_percent,
            "memory_usage": metrics.memory_usage,
            "memory_limit": metrics.memory_limit,
            "rx_rate": metrics.network_rx_rate,
            "tx_rate": metrics.network_tx_rate,
            "timestamp": metrics.timestamp
        })

        # Aggregate if we have enough samples (1 minute worth at 2s intervals = ~30 samples)
        if len(self._aggregation_buffer[service]) >= 30:
            self._flush_buffer(service)

    def _flush_buffer(self, service_name: str):
        """Flush aggregation buffer to database."""
        buffer = self._aggregation_buffer.get(service_name, [])
        if not buffer:
            return

        cpu_values = [b["cpu"] for b in buffer]
        memory_values = [b["memory"] for b in buffer]
        rx_values = [b["rx_rate"] for b in buffer]
        tx_values = [b["tx_rate"] for b in buffer]

        snapshot = MetricsSnapshotModel(
            service_name=service_name,
            timestamp=datetime.utcnow(),
            cpu_avg=sum(cpu_values) / len(cpu_values),
            cpu_max=max(cpu_values),
            memory_avg=sum(memory_values) / len(memory_values),
            memory_max=max(memory_values),
            memory_usage_avg=int(sum(b["memory_usage"] for b in buffer) / len(buffer)),
            memory_limit=buffer[-1]["memory_limit"],
            network_rx_rate_avg=sum(rx_values) / len(rx_values),
            network_tx_rate_avg=sum(tx_values) / len(tx_values)
        )

        self.db.add(snapshot)
        self.db.commit()

        # Clear buffer
        self._aggregation_buffer[service_name] = []

        # Prune old data (keep 24 hours)
        cutoff = datetime.utcnow() - timedelta(hours=24)
        self.db.query(MetricsSnapshotModel).filter(
            MetricsSnapshotModel.timestamp < cutoff
        ).delete()
        self.db.commit()

    def check_and_create_alerts(
        self,
        metrics: ContainerMetrics
    ) -> List[HealthAlert]:
        """Check metrics against thresholds and create alerts."""
        alerts = []

        # CPU alert
        if metrics.cpu_percent >= THRESHOLDS["cpu_critical"]:
            alert = self._create_alert(
                metrics.service_name,
                AlertType.HIGH_CPU,
                AlertSeverity.CRITICAL,
                f"CPU usage critical: {metrics.cpu_percent:.1f}%"
            )
            if alert:
                alerts.append(alert)
        elif metrics.cpu_percent >= THRESHOLDS["cpu_warning"]:
            alert = self._create_alert(
                metrics.service_name,
                AlertType.HIGH_CPU,
                AlertSeverity.WARNING,
                f"CPU usage high: {metrics.cpu_percent:.1f}%"
            )
            if alert:
                alerts.append(alert)

        # Memory alert
        if metrics.memory_percent >= THRESHOLDS["memory_critical"]:
            alert = self._create_alert(
                metrics.service_name,
                AlertType.HIGH_MEMORY,
                AlertSeverity.CRITICAL,
                f"Memory usage critical: {metrics.memory_percent:.1f}%"
            )
            if alert:
                alerts.append(alert)
        elif metrics.memory_percent >= THRESHOLDS["memory_warning"]:
            alert = self._create_alert(
                metrics.service_name,
                AlertType.HIGH_MEMORY,
                AlertSeverity.WARNING,
                f"Memory usage high: {metrics.memory_percent:.1f}%"
            )
            if alert:
                alerts.append(alert)

        return alerts

    def _create_alert(
        self,
        service_name: str,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        details: Dict = None
    ) -> Optional[HealthAlert]:
        """Create an alert if one doesn't exist recently."""
        # Check for recent duplicate
        recent = datetime.utcnow() - timedelta(minutes=5)
        existing = self.db.query(HealthAlertModel).filter(
            HealthAlertModel.service_name == service_name,
            HealthAlertModel.alert_type == alert_type.value,
            HealthAlertModel.timestamp > recent,
            HealthAlertModel.acknowledged == False
        ).first()

        if existing:
            return None

        alert_id = str(uuid.uuid4())
        db_alert = HealthAlertModel(
            alert_id=alert_id,
            service_name=service_name,
            alert_type=alert_type.value,
            severity=severity.value,
            message=message,
            details=json.dumps(details) if details else None
        )
        self.db.add(db_alert)
        self.db.commit()

        return HealthAlert(
            id=alert_id,
            service_name=service_name,
            alert_type=alert_type,
            severity=severity,
            message=message,
            timestamp=datetime.utcnow(),
            details=details
        )

    def get_active_alerts(
        self,
        service_name: Optional[str] = None,
        limit: int = 50
    ) -> List[HealthAlert]:
        """Get active (unacknowledged) alerts."""
        query = self.db.query(HealthAlertModel).filter(
            HealthAlertModel.acknowledged == False
        )

        if service_name:
            query = query.filter(HealthAlertModel.service_name == service_name)

        alerts = query.order_by(desc(HealthAlertModel.timestamp)).limit(limit).all()

        return [
            HealthAlert(
                id=a.alert_id,
                service_name=a.service_name,
                alert_type=AlertType(a.alert_type),
                severity=AlertSeverity(a.severity),
                message=a.message,
                timestamp=a.timestamp,
                acknowledged=a.acknowledged,
                details=json.loads(a.details) if a.details else None
            )
            for a in alerts
        ]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        alert = self.db.query(HealthAlertModel).filter(
            HealthAlertModel.alert_id == alert_id
        ).first()

        if not alert:
            return False

        alert.acknowledged = True
        alert.acknowledged_at = datetime.utcnow()
        self.db.commit()
        return True

    def get_diagnostics(self, service_name: str) -> DiagnosticsResponse:
        """Run diagnostics for a service."""
        issues = []

        # Get current metrics
        metrics = self.get_current_metrics(service_name)
        if metrics:
            issues.extend(analyze_metrics(service_name, metrics.model_dump()))

        # Get recent logs and analyze
        container = self.docker.get_container(service_name)
        if container:
            try:
                container_obj = self.docker.client.containers.get(container["full_id"])
                logs = container_obj.logs(tail=200).decode("utf-8", errors="replace")
                log_lines = logs.strip().split("\n")
                issues.extend(analyze_logs(service_name, log_lines))
            except Exception:
                pass

        # Analyze restart pattern
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        restarts = self.db.query(ServiceRestartEvent).filter(
            ServiceRestartEvent.service_name == service_name,
            ServiceRestartEvent.timestamp > hour_ago
        ).all()

        restart_times = [r.timestamp for r in restarts]
        in_crash_loop, restart_issue = analyze_restart_pattern(service_name, restart_times)
        if restart_issue:
            issues.append(restart_issue)

        # Get uptime
        uptime = None
        last_restart = None
        if container:
            try:
                container_obj = self.docker.client.containers.get(container["full_id"])
                started_at = container_obj.attrs.get("State", {}).get("StartedAt")
                if started_at:
                    start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                    uptime = int((datetime.now(start_time.tzinfo) - start_time).total_seconds())
                    last_restart = start_time.replace(tzinfo=None)
            except Exception:
                pass

        return DiagnosticsResponse(
            service_name=service_name,
            issues=issues,
            restart_recommended=should_recommend_restart(issues, len(restart_times)),
            last_restart=last_restart,
            uptime_seconds=uptime
        )

    def record_restart(self, service_name: str, reason: str = None, triggered_by: str = "user"):
        """Record a service restart event."""
        event = ServiceRestartEvent(
            service_name=service_name,
            reason=reason,
            triggered_by=triggered_by
        )
        self.db.add(event)
        self.db.commit()
