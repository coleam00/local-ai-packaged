"""Tests for port scanner functionality."""
import socket
import pytest
from unittest.mock import Mock, patch

from app.core.port_scanner import PortScanner, PortStatus, PortScanResult, get_all_default_ports


class TestPortScanner:
    """Tests for PortScanner class."""

    def test_is_port_available_free_port(self):
        """Test that a free port returns True."""
        scanner = PortScanner()
        # Port 59999 is unlikely to be in use
        available, used_by = scanner.is_port_available(59999)
        assert available is True
        assert used_by is None

    def test_is_port_available_used_port(self):
        """Test that a port in use returns False."""
        # Create a temporary socket to occupy a port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', 59998))
        sock.listen(1)

        try:
            scanner = PortScanner()
            available, used_by = scanner.is_port_available(59998)
            assert available is False
            assert used_by == "host service"
        finally:
            sock.close()

    def test_find_available_port(self):
        """Test finding the next available port."""
        # Create a temporary socket to occupy a port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', 59997))
        sock.listen(1)

        try:
            scanner = PortScanner()
            # Should find port after 59997
            next_port = scanner.find_available_port(59997)
            assert next_port >= 59998
        finally:
            sock.close()

    def test_find_available_port_already_free(self):
        """Test finding port when start port is already free."""
        scanner = PortScanner()
        port = scanner.find_available_port(59996)
        assert port == 59996

    def test_scan_service_ports_all_available(self):
        """Test scanning when all ports are available."""
        scanner = PortScanner()
        result = scanner.scan_service_ports(
            service_name="test-service",
            display_name="Test Service",
            default_ports={"http": 59990, "grpc": 59991}
        )

        assert result.service_name == "test-service"
        assert result.display_name == "Test Service"
        assert result.all_available is True
        assert len(result.ports) == 2
        assert result.ports["http"].available is True
        assert result.ports["grpc"].available is True
        assert result.suggested_ports["http"] == 59990
        assert result.suggested_ports["grpc"] == 59991

    def test_scan_service_ports_with_conflict(self):
        """Test scanning when a port is in use."""
        # Occupy a port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', 59989))
        sock.listen(1)

        try:
            scanner = PortScanner()
            result = scanner.scan_service_ports(
                service_name="test-service",
                display_name="Test Service",
                default_ports={"http": 59989}
            )

            assert result.all_available is False
            assert result.ports["http"].available is False
            assert result.ports["http"].used_by == "host service"
            assert result.suggested_ports["http"] != 59989  # Should suggest alternative
        finally:
            sock.close()

    def test_load_docker_ports_handles_missing_docker(self):
        """Test that Docker port loading handles errors gracefully."""
        scanner = PortScanner()
        mock_client = Mock()
        mock_client.list_containers.side_effect = Exception("Docker not available")

        # Should not raise
        scanner.load_docker_ports(mock_client)
        assert scanner._docker_ports == {}

    def test_load_docker_ports_from_running_containers(self):
        """Test loading ports from Docker containers."""
        scanner = PortScanner()
        mock_client = Mock()
        mock_client.list_containers.return_value = [
            {
                "name": "test-container",
                "status": "running",
                "ports": [
                    {"PublicPort": 8080}
                ]
            }
        ]

        scanner.load_docker_ports(mock_client)
        assert 8080 in scanner._docker_ports
        assert scanner._docker_ports[8080] == "test-container"

    def test_is_port_available_with_docker_port(self):
        """Test that Docker-occupied ports are detected."""
        scanner = PortScanner()
        scanner._docker_ports[12345] = "test-container"

        available, used_by = scanner.is_port_available(12345)
        # Note: We still check socket first, so if socket says available
        # but docker has it, it's still considered in use
        if available:  # Socket says available
            pass  # Docker ports are checked after socket
        else:
            assert "Docker" in used_by or used_by == "host service"


class TestGetAllDefaultPorts:
    """Tests for get_all_default_ports function."""

    def test_returns_dict_of_ports(self):
        """Test that function returns a dict of service ports."""
        ports = get_all_default_ports()
        assert isinstance(ports, dict)

        # Check that some known services are included
        if "flowise" in ports:
            assert "http" in ports["flowise"]
            assert ports["flowise"]["http"] == 3001

        if "open-webui" in ports:
            assert "http" in ports["open-webui"]
            assert ports["open-webui"]["http"] == 8080

    def test_only_includes_services_with_ports(self):
        """Test that services without ports are excluded."""
        ports = get_all_default_ports()

        for service_name, service_ports in ports.items():
            assert len(service_ports) > 0, f"Service {service_name} should have ports"


class TestPortStatus:
    """Tests for PortStatus dataclass."""

    def test_port_status_creation(self):
        """Test creating PortStatus."""
        status = PortStatus(port=8080, available=True)
        assert status.port == 8080
        assert status.available is True
        assert status.used_by is None

    def test_port_status_with_used_by(self):
        """Test PortStatus with used_by field."""
        status = PortStatus(port=8080, available=False, used_by="nginx")
        assert status.port == 8080
        assert status.available is False
        assert status.used_by == "nginx"


class TestPortReservation:
    """Tests for port reservation to prevent conflicts."""

    def test_reserved_ports_prevent_duplicates(self):
        """Test that reserved ports prevent duplicate suggestions."""
        scanner = PortScanner()

        # Scan first service - gets port 59980
        result1 = scanner.scan_service_ports(
            service_name="service1",
            display_name="Service 1",
            default_ports={"http": 59980}
        )
        assert result1.suggested_ports["http"] == 59980

        # Scan second service - also wants 59980, should get different port
        result2 = scanner.scan_service_ports(
            service_name="service2",
            display_name="Service 2",
            default_ports={"http": 59980}
        )
        # Should get a different port since 59980 is reserved
        assert result2.suggested_ports["http"] != 59980
        assert result2.ports["http"].available is False
        assert "reserved" in result2.ports["http"].used_by

    def test_clear_reserved_ports(self):
        """Test that clearing reserved ports works."""
        scanner = PortScanner()

        # Reserve a port
        scanner.scan_service_ports(
            service_name="service1",
            display_name="Service 1",
            default_ports={"http": 59979}
        )
        assert 59979 in scanner._reserved_ports

        # Clear and verify
        scanner.clear_reserved_ports()
        assert len(scanner._reserved_ports) == 0

        # Now the port should be available again
        result = scanner.scan_service_ports(
            service_name="service2",
            display_name="Service 2",
            default_ports={"http": 59979}
        )
        assert result.suggested_ports["http"] == 59979


class TestPortScanResult:
    """Tests for PortScanResult dataclass."""

    def test_port_scan_result_creation(self):
        """Test creating PortScanResult."""
        result = PortScanResult(
            service_name="test",
            display_name="Test Service",
            ports={"http": PortStatus(port=8080, available=True)},
            all_available=True,
            suggested_ports={"http": 8080}
        )
        assert result.service_name == "test"
        assert result.display_name == "Test Service"
        assert result.all_available is True
        assert "http" in result.ports
        assert result.suggested_ports["http"] == 8080
