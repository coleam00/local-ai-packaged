from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from ..schemas.metrics import DiagnosticResult, AlertSeverity, AlertType
import re


# Threshold configurations
THRESHOLDS = {
    "cpu_warning": 80.0,
    "cpu_critical": 95.0,
    "memory_warning": 85.0,
    "memory_critical": 95.0,
    "restart_count_warning": 3,  # restarts in last hour
    "restart_count_critical": 5,
}

# Known error patterns in logs
ERROR_PATTERNS = {
    "oom": (
        re.compile(r"(out of memory|oom|killed process|memory allocation failed)", re.I),
        AlertType.OOM_KILLED,
        "Container ran out of memory"
    ),
    "connection_refused": (
        re.compile(r"(connection refused|ECONNREFUSED|connect ECONNREFUSED)", re.I),
        AlertType.NETWORK_ERROR,
        "Service cannot connect to a dependency"
    ),
    "health_check": (
        re.compile(r"(health check|healthcheck).*(fail|error|timeout)", re.I),
        AlertType.HEALTH_CHECK_FAILED,
        "Health check is failing"
    ),
}

# Service-specific diagnostics
SERVICE_DIAGNOSTICS = {
    "postgres": {
        "common_issues": [
            {
                "pattern": re.compile(r"FATAL.*password authentication failed", re.I),
                "issue": "Authentication failure",
                "recommendation": "Check POSTGRES_PASSWORD in .env matches across services"
            },
            {
                "pattern": re.compile(r"could not connect to server", re.I),
                "issue": "Database connection failed",
                "recommendation": "Ensure postgres container is running and healthy before dependent services"
            },
        ]
    },
    "ollama": {
        "common_issues": [
            {
                "pattern": re.compile(r"(CUDA|GPU|nvidia).*(error|failed|not found)", re.I),
                "issue": "GPU initialization failed",
                "recommendation": "Check NVIDIA drivers and ensure gpu-nvidia profile is used"
            },
        ]
    },
    "supabase": {
        "common_issues": [
            {
                "pattern": re.compile(r"JWT.*invalid|token.*expired", re.I),
                "issue": "JWT token issue",
                "recommendation": "Regenerate JWT_SECRET and ANON_KEY in .env"
            },
        ]
    },
}


def analyze_metrics(
    service_name: str,
    current_metrics: Dict,
    recent_metrics: List[Dict] = None
) -> List[DiagnosticResult]:
    """Analyze metrics and return diagnostic results."""
    issues = []

    cpu = current_metrics.get("cpu_percent", 0)
    memory = current_metrics.get("memory_percent", 0)

    # CPU analysis
    if cpu >= THRESHOLDS["cpu_critical"]:
        issues.append(DiagnosticResult(
            service_name=service_name,
            issue="Critical CPU usage",
            description=f"CPU usage is at {cpu:.1f}%",
            severity=AlertSeverity.CRITICAL,
            recommendation="Consider scaling or optimizing the service. Check for infinite loops or resource-intensive operations.",
            auto_fixable=False
        ))
    elif cpu >= THRESHOLDS["cpu_warning"]:
        issues.append(DiagnosticResult(
            service_name=service_name,
            issue="High CPU usage",
            description=f"CPU usage is at {cpu:.1f}%",
            severity=AlertSeverity.WARNING,
            recommendation="Monitor for continued high usage. May need resource adjustment.",
            auto_fixable=False
        ))

    # Memory analysis
    if memory >= THRESHOLDS["memory_critical"]:
        issues.append(DiagnosticResult(
            service_name=service_name,
            issue="Critical memory usage",
            description=f"Memory usage is at {memory:.1f}%",
            severity=AlertSeverity.CRITICAL,
            recommendation="Service may crash soon. Consider increasing memory limit or restarting.",
            auto_fixable=True  # Restart can help
        ))
    elif memory >= THRESHOLDS["memory_warning"]:
        issues.append(DiagnosticResult(
            service_name=service_name,
            issue="High memory usage",
            description=f"Memory usage is at {memory:.1f}%",
            severity=AlertSeverity.WARNING,
            recommendation="Monitor memory growth. Check for memory leaks.",
            auto_fixable=False
        ))

    return issues


def analyze_logs(
    service_name: str,
    log_lines: List[str],
    limit: int = 100
) -> List[DiagnosticResult]:
    """Analyze recent logs for known error patterns."""
    issues = []
    seen_issues = set()

    # Check last N lines
    recent_logs = log_lines[-limit:] if len(log_lines) > limit else log_lines

    # Check generic patterns
    for name, (pattern, alert_type, description) in ERROR_PATTERNS.items():
        for line in recent_logs:
            if pattern.search(line) and name not in seen_issues:
                seen_issues.add(name)
                severity = AlertSeverity.CRITICAL if "oom" in name else AlertSeverity.WARNING
                issues.append(DiagnosticResult(
                    service_name=service_name,
                    issue=description,
                    description=f"Found in logs: {line[:200]}",
                    severity=severity,
                    recommendation=get_recommendation_for_alert(alert_type),
                    auto_fixable=alert_type == AlertType.OOM_KILLED
                ))
                break

    # Check service-specific patterns
    service_config = SERVICE_DIAGNOSTICS.get(service_name, {})
    for issue_config in service_config.get("common_issues", []):
        pattern = issue_config["pattern"]
        for line in recent_logs:
            if pattern.search(line) and issue_config["issue"] not in seen_issues:
                seen_issues.add(issue_config["issue"])
                issues.append(DiagnosticResult(
                    service_name=service_name,
                    issue=issue_config["issue"],
                    description=f"Found in logs: {line[:200]}",
                    severity=AlertSeverity.WARNING,
                    recommendation=issue_config["recommendation"],
                    auto_fixable=False
                ))
                break

    return issues


def analyze_restart_pattern(
    service_name: str,
    restart_times: List[datetime],
    current_time: datetime = None
) -> Tuple[bool, Optional[DiagnosticResult]]:
    """Analyze restart patterns to detect crash loops."""
    if not restart_times:
        return False, None

    current_time = current_time or datetime.utcnow()
    hour_ago = current_time - timedelta(hours=1)

    recent_restarts = [t for t in restart_times if t > hour_ago]
    count = len(recent_restarts)

    if count >= THRESHOLDS["restart_count_critical"]:
        return True, DiagnosticResult(
            service_name=service_name,
            issue="Crash loop detected",
            description=f"Service has restarted {count} times in the last hour",
            severity=AlertSeverity.CRITICAL,
            recommendation="Service is in a crash loop. Check logs for root cause before restarting again.",
            auto_fixable=False
        )
    elif count >= THRESHOLDS["restart_count_warning"]:
        return False, DiagnosticResult(
            service_name=service_name,
            issue="Frequent restarts",
            description=f"Service has restarted {count} times in the last hour",
            severity=AlertSeverity.WARNING,
            recommendation="Monitor service stability. Check logs for errors.",
            auto_fixable=False
        )

    return False, None


def should_recommend_restart(
    issues: List[DiagnosticResult],
    restart_count_last_hour: int
) -> bool:
    """Determine if restart should be recommended based on issues."""
    # Don't recommend restart if already in crash loop
    if restart_count_last_hour >= THRESHOLDS["restart_count_warning"]:
        return False

    # Recommend restart for auto-fixable critical issues
    for issue in issues:
        if issue.auto_fixable and issue.severity == AlertSeverity.CRITICAL:
            return True

    return False


def get_recommendation_for_alert(alert_type: AlertType) -> str:
    """Get recommendation text for an alert type."""
    recommendations = {
        AlertType.HIGH_CPU: "Consider scaling the service or investigating resource-intensive operations",
        AlertType.HIGH_MEMORY: "Check for memory leaks or increase memory limit",
        AlertType.CONTAINER_RESTART: "Check logs for crash cause before restarting again",
        AlertType.HEALTH_CHECK_FAILED: "Check service logs and verify dependent services are healthy",
        AlertType.OOM_KILLED: "Increase memory limit or optimize memory usage. Restart may help temporarily.",
        AlertType.NETWORK_ERROR: "Verify dependent services are running and network connectivity",
    }
    return recommendations.get(alert_type, "Check service logs for more details")
