"""
Unit tests for health and readiness endpoints.

Tests:
- get_health_status() always returns healthy
- get_readiness_status() reflects cache state correctly
- Statistics accuracy (counts match cache)
- Status transitions (not_ready → ready)
- Heartbeat logging
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.retrieval.health import (
    get_health_status,
    get_readiness_status,
    log_heartbeat,
    format_readiness_report,
    HealthStatus,
    ReadinessStatus
)
from src.retrieval.retriever import TemplateRetriever


class TestGetHealthStatus:
    """Tests for get_health_status function."""

    def test_health_status_always_healthy(self):
        """Test that health check always returns healthy."""
        # Act
        status = get_health_status()

        # Assert
        assert status["status"] == HealthStatus.HEALTHY
        assert "timestamp" in status

    def test_health_status_timestamp_format(self):
        """Test that timestamp is in ISO 8601 format."""
        # Act
        status = get_health_status()

        # Assert
        # Should be able to parse timestamp
        timestamp = datetime.fromisoformat(status["timestamp"])
        assert isinstance(timestamp, datetime)


class TestGetReadinessStatus:
    """Tests for get_readiness_status function."""

    def test_readiness_with_none_retriever(self):
        """Test readiness status when retriever is None."""
        # Act
        status = get_readiness_status(None)

        # Assert
        assert status["status"] == ReadinessStatus.NOT_READY
        assert status["ready"] is False
        assert status["total_templates"] == 0
        assert status["embedded_templates"] == 0
        assert status["failed_templates"] == 0
        assert status["precompute_time_seconds"] is None
        assert "not initialized" in status["message"].lower()

    def test_readiness_with_not_ready_retriever(self):
        """Test readiness status when retriever not ready."""
        # Arrange
        mock_retriever = Mock(spec=TemplateRetriever)
        mock_retriever.is_ready.return_value = False

        # Act
        status = get_readiness_status(mock_retriever)

        # Assert
        assert status["status"] == ReadinessStatus.NOT_READY
        assert status["ready"] is False
        assert status["total_templates"] == 0

    def test_readiness_with_ready_retriever(self):
        """Test readiness status when retriever is ready."""
        # Arrange
        mock_retriever = Mock(spec=TemplateRetriever)
        mock_retriever.is_ready.return_value = True
        mock_retriever.get_cache_stats.return_value = {
            "total_templates": 150,
            "categories": 6,
            "subcategories": 25,
            "precompute_time_seconds": 45.2,
            "memory_estimate_mb": 1.8
        }

        # Act
        status = get_readiness_status(mock_retriever)

        # Assert
        assert status["status"] == ReadinessStatus.READY
        assert status["ready"] is True
        assert status["total_templates"] == 150
        assert status["embedded_templates"] == 150
        assert status["failed_templates"] == 0
        assert status["categories"] == 6
        assert status["subcategories"] == 25
        assert status["precompute_time_seconds"] == 45.2
        assert status["memory_estimate_mb"] == 1.8
        assert "ready" in status["message"].lower()

    def test_readiness_status_includes_timestamp(self):
        """Test that readiness status includes ISO 8601 timestamp."""
        # Arrange
        mock_retriever = Mock(spec=TemplateRetriever)
        mock_retriever.is_ready.return_value = True
        mock_retriever.get_cache_stats.return_value = {
            "total_templates": 100,
            "categories": 5,
            "subcategories": 15,
            "precompute_time_seconds": 30.0,
            "memory_estimate_mb": 1.0
        }

        # Act
        status = get_readiness_status(mock_retriever)

        # Assert
        assert "timestamp" in status
        # Should be able to parse timestamp
        timestamp = datetime.fromisoformat(status["timestamp"])
        assert isinstance(timestamp, datetime)

    def test_readiness_zero_templates_not_ready(self):
        """Test that zero templates results in not ready status."""
        # Arrange
        mock_retriever = Mock(spec=TemplateRetriever)
        mock_retriever.is_ready.return_value = True
        mock_retriever.get_cache_stats.return_value = {
            "total_templates": 0,  # No templates!
            "categories": 0,
            "subcategories": 0,
            "precompute_time_seconds": 0.0,
            "memory_estimate_mb": 0.0
        }

        # Act
        status = get_readiness_status(mock_retriever)

        # Assert
        assert status["status"] == ReadinessStatus.NOT_READY
        assert status["ready"] is False
        assert "no templates" in status["message"].lower()

    def test_readiness_status_fields_complete(self):
        """Test that readiness status includes all required fields."""
        # Arrange
        mock_retriever = Mock(spec=TemplateRetriever)
        mock_retriever.is_ready.return_value = True
        mock_retriever.get_cache_stats.return_value = {
            "total_templates": 50,
            "categories": 3,
            "subcategories": 10,
            "precompute_time_seconds": 15.0,
            "memory_estimate_mb": 0.5
        }

        # Act
        status = get_readiness_status(mock_retriever)

        # Assert - check all required fields
        required_fields = [
            "status", "ready", "total_templates", "embedded_templates",
            "failed_templates", "categories", "subcategories",
            "precompute_time_seconds", "memory_estimate_mb",
            "timestamp", "message"
        ]
        for field in required_fields:
            assert field in status, f"Missing field: {field}"


class TestLogHeartbeat:
    """Tests for log_heartbeat function."""

    @patch('src.retrieval.health.logger')
    def test_heartbeat_logs_readiness_info(self, mock_logger):
        """Test that heartbeat logs readiness information."""
        # Arrange
        mock_retriever = Mock(spec=TemplateRetriever)
        mock_retriever.is_ready.return_value = True
        mock_retriever.get_cache_stats.return_value = {
            "total_templates": 100,
            "categories": 5,
            "subcategories": 15,
            "precompute_time_seconds": 30.0,
            "memory_estimate_mb": 1.0
        }

        # Act
        log_heartbeat(mock_retriever)

        # Assert
        mock_logger.info.assert_called_once()
        log_message = mock_logger.info.call_args[0][0]

        # Verify key information in log message
        assert "Heartbeat" in log_message
        assert "status=" in log_message
        assert "templates=" in log_message
        assert "ready=" in log_message

    @patch('src.retrieval.health.logger')
    def test_heartbeat_with_none_retriever(self, mock_logger):
        """Test heartbeat logging with None retriever."""
        # Act
        log_heartbeat(None)

        # Assert
        mock_logger.info.assert_called_once()
        log_message = mock_logger.info.call_args[0][0]
        assert "not_initialized" in log_message or "not_ready" in log_message


class TestFormatReadinessReport:
    """Tests for format_readiness_report function."""

    def test_format_report_includes_all_info(self):
        """Test that formatted report includes all key information."""
        # Arrange
        mock_retriever = Mock(spec=TemplateRetriever)
        mock_retriever.is_ready.return_value = True
        mock_retriever.get_cache_stats.return_value = {
            "total_templates": 187,
            "categories": 6,
            "subcategories": 35,
            "precompute_time_seconds": 45.3,
            "memory_estimate_mb": 2.1
        }

        # Act
        report = format_readiness_report(mock_retriever)

        # Assert
        # Check for key sections
        assert "Retrieval Module Readiness Report" in report
        assert "Status:" in report
        assert "Ready:" in report
        assert "Templates:" in report
        assert "Total: 187" in report
        assert "Embedded: 187" in report
        assert "Categories: 6" in report
        assert "Subcategories: 35" in report
        assert "Precompute Time:" in report
        assert "45.3s" in report
        assert "Memory Estimate:" in report
        assert "2.1" in report or "2.10" in report

    def test_format_report_with_none_retriever(self):
        """Test formatted report when retriever is None."""
        # Act
        report = format_readiness_report(None)

        # Assert
        assert "not_initialized" in report or "not_ready" in report
        assert "Total: 0" in report

    def test_format_report_not_ready_shows_no_emoji(self):
        """Test that not-ready status shows ❌."""
        # Arrange
        mock_retriever = Mock(spec=TemplateRetriever)
        mock_retriever.is_ready.return_value = False

        # Act
        report = format_readiness_report(mock_retriever)

        # Assert
        assert "❌" in report or "No" in report

    def test_format_report_ready_shows_yes_emoji(self):
        """Test that ready status shows ✅."""
        # Arrange
        mock_retriever = Mock(spec=TemplateRetriever)
        mock_retriever.is_ready.return_value = True
        mock_retriever.get_cache_stats.return_value = {
            "total_templates": 50,
            "categories": 3,
            "subcategories": 10,
            "precompute_time_seconds": 10.0,
            "memory_estimate_mb": 0.5
        }

        # Act
        report = format_readiness_report(mock_retriever)

        # Assert
        assert "✅" in report or "Yes" in report

    def test_format_report_is_multiline(self):
        """Test that report is formatted with multiple lines."""
        # Arrange
        mock_retriever = Mock(spec=TemplateRetriever)
        mock_retriever.is_ready.return_value = True
        mock_retriever.get_cache_stats.return_value = {
            "total_templates": 100,
            "categories": 5,
            "subcategories": 15,
            "precompute_time_seconds": 30.0,
            "memory_estimate_mb": 1.0
        }

        # Act
        report = format_readiness_report(mock_retriever)

        # Assert
        lines = report.split("\n")
        assert len(lines) > 10, "Report should have multiple lines"
        assert any("=" in line for line in lines), "Report should have separator lines"
