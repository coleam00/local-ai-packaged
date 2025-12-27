from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Index
from sqlalchemy.sql import func
from ..database import Base


class MetricsSnapshot(Base):
    """Stores aggregated metrics snapshots (1-minute intervals)."""
    __tablename__ = "metrics_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_name = Column(String(255), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    cpu_avg = Column(Float, default=0.0)
    cpu_max = Column(Float, default=0.0)
    memory_avg = Column(Float, default=0.0)
    memory_max = Column(Float, default=0.0)
    memory_usage_avg = Column(Integer, default=0)
    memory_limit = Column(Integer, default=0)
    network_rx_rate_avg = Column(Float, default=0.0)
    network_tx_rate_avg = Column(Float, default=0.0)

    __table_args__ = (
        Index('ix_metrics_service_time', 'service_name', 'timestamp'),
    )


class HealthAlert(Base):
    """Stores health alerts for services."""
    __tablename__ = "health_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(36), unique=True, nullable=False, index=True)
    service_name = Column(String(255), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True)  # JSON string
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index('ix_alerts_service_time', 'service_name', 'timestamp'),
    )


class ServiceRestartEvent(Base):
    """Tracks service restart events for pattern analysis."""
    __tablename__ = "service_restart_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_name = Column(String(255), nullable=False, index=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    reason = Column(String(255), nullable=True)
    triggered_by = Column(String(50), default="user")  # user, auto, system

    __table_args__ = (
        Index('ix_restarts_service_time', 'service_name', 'timestamp'),
    )
