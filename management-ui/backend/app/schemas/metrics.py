from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, Enum):
    HIGH_CPU = "high_cpu"
    HIGH_MEMORY = "high_memory"
    CONTAINER_RESTART = "container_restart"
    HEALTH_CHECK_FAILED = "health_check_failed"
    OOM_KILLED = "oom_killed"
    NETWORK_ERROR = "network_error"


class ContainerMetrics(BaseModel):
    """Real-time metrics for a single container."""
    service_name: str
    container_id: str
    timestamp: datetime
    cpu_percent: float = Field(ge=0, description="CPU usage percentage")
    memory_usage: int = Field(ge=0, description="Memory usage in bytes")
    memory_limit: int = Field(ge=0, description="Memory limit in bytes")
    memory_percent: float = Field(ge=0, le=100, description="Memory usage percentage")
    network_rx_bytes: int = Field(ge=0, description="Network bytes received")
    network_tx_bytes: int = Field(ge=0, description="Network bytes transmitted")
    network_rx_rate: float = Field(ge=0, description="Network receive rate bytes/sec")
    network_tx_rate: float = Field(ge=0, description="Network transmit rate bytes/sec")
    block_read_bytes: int = Field(ge=0, default=0)
    block_write_bytes: int = Field(ge=0, default=0)


class MetricsSnapshot(BaseModel):
    """Aggregated metrics snapshot for storage."""
    service_name: str
    timestamp: datetime
    cpu_avg: float
    cpu_max: float
    memory_avg: float
    memory_max: float
    network_rx_rate_avg: float
    network_tx_rate_avg: float


class MetricsHistoryResponse(BaseModel):
    """Response for metrics history query."""
    service_name: str
    start_time: datetime
    end_time: datetime
    data_points: List[MetricsSnapshot]
    granularity_seconds: int = 60


class HealthAlert(BaseModel):
    """Health alert notification."""
    id: str
    service_name: str
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    timestamp: datetime
    acknowledged: bool = False
    details: Optional[Dict] = None


class DiagnosticResult(BaseModel):
    """Result of diagnostic check."""
    service_name: str
    issue: str
    description: str
    severity: AlertSeverity
    recommendation: str
    auto_fixable: bool = False


class DiagnosticsResponse(BaseModel):
    """Response for diagnostics endpoint."""
    service_name: str
    issues: List[DiagnosticResult]
    restart_recommended: bool
    last_restart: Optional[datetime] = None
    uptime_seconds: Optional[int] = None


class AllMetricsResponse(BaseModel):
    """Response for all services metrics."""
    metrics: List[ContainerMetrics]
    timestamp: datetime
