"""Tests for gateway status widget."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from openclaw_dash.widgets.gateway_status import (
    AMBER,
    AMBER_BRIGHT,
    AMBER_DIM,
    ConnectionStatus,
    GatewayStatusSummary,
    GatewayStatusWidget,
    _calculate_total_tokens,
    _format_tokens,
    _format_uptime,
    get_connection_color,
    get_connection_icon,
)


class TestConnectionStatus:
    """Tests for ConnectionStatus class."""

    def test_status_values(self):
        """Test that all status values are correct."""
        assert ConnectionStatus.CONNECTED == "connected"
        assert ConnectionStatus.DISCONNECTED == "disconnected"
        assert ConnectionStatus.CONNECTING == "connecting"


class TestConnectionHelpers:
    """Tests for connection helper functions."""

    def test_get_connection_icon_connected(self):
        """Test icon for connected status."""
        assert get_connection_icon(ConnectionStatus.CONNECTED) == "●"

    def test_get_connection_icon_disconnected(self):
        """Test icon for disconnected status."""
        assert get_connection_icon(ConnectionStatus.DISCONNECTED) == "○"

    def test_get_connection_icon_connecting(self):
        """Test icon for connecting status."""
        assert get_connection_icon(ConnectionStatus.CONNECTING) == "◐"

    def test_get_connection_icon_invalid(self):
        """Test icon for invalid status returns default."""
        assert get_connection_icon("invalid") == "?"

    def test_get_connection_color_connected(self):
        """Test color for connected status is amber."""
        assert get_connection_color(ConnectionStatus.CONNECTED) == AMBER

    def test_get_connection_color_disconnected(self):
        """Test color for disconnected status is red."""
        assert get_connection_color(ConnectionStatus.DISCONNECTED) == "red"

    def test_get_connection_color_connecting(self):
        """Test color for connecting status is dim amber."""
        assert get_connection_color(ConnectionStatus.CONNECTING) == AMBER_DIM

    def test_get_connection_color_invalid(self):
        """Test color for invalid status returns default white."""
        assert get_connection_color("invalid") == "white"


class TestFormatUptime:
    """Tests for uptime formatting."""

    def test_format_uptime_seconds(self):
        """Test uptime formatting in seconds."""
        now = datetime.now()
        started_at = now - timedelta(seconds=45)
        result = _format_uptime(started_at)
        assert "s" in result
        assert "m" not in result

    def test_format_uptime_minutes(self):
        """Test uptime formatting in minutes."""
        now = datetime.now()
        started_at = now - timedelta(minutes=15, seconds=30)
        result = _format_uptime(started_at)
        assert "m" in result
        assert "h" not in result

    def test_format_uptime_hours(self):
        """Test uptime formatting in hours."""
        now = datetime.now()
        started_at = now - timedelta(hours=3, minutes=45)
        result = _format_uptime(started_at)
        assert "h" in result
        assert "d" not in result

    def test_format_uptime_days(self):
        """Test uptime formatting in days."""
        now = datetime.now()
        started_at = now - timedelta(days=2, hours=5)
        result = _format_uptime(started_at)
        assert "d" in result

    def test_format_uptime_none(self):
        """Test uptime formatting with None returns dash."""
        assert _format_uptime(None) == "—"

    def test_format_uptime_iso_string(self):
        """Test uptime formatting from ISO string."""
        now = datetime.now()
        started_at = (now - timedelta(hours=1)).isoformat()
        result = _format_uptime(started_at)
        assert "h" in result or "m" in result

    def test_format_uptime_future(self):
        """Test uptime formatting for future timestamp."""
        now = datetime.now()
        started_at = now + timedelta(minutes=5)
        result = _format_uptime(started_at)
        assert result == "just started"


class TestFormatTokens:
    """Tests for token formatting."""

    def test_format_tokens_small(self):
        """Test formatting small token counts."""
        assert _format_tokens(500) == "500"

    def test_format_tokens_thousands(self):
        """Test formatting thousands of tokens."""
        result = _format_tokens(45200)
        assert "k" in result
        assert "45.2" in result

    def test_format_tokens_millions(self):
        """Test formatting millions of tokens."""
        result = _format_tokens(1_250_000)
        assert "M" in result
        assert "1.25" in result

    def test_format_tokens_zero(self):
        """Test formatting zero tokens."""
        assert _format_tokens(0) == "0"


class TestCalculateTotalTokens:
    """Tests for total token calculation."""

    def test_calculate_total_tokens_single_session(self):
        """Test calculating tokens for single session."""
        sessions_data = {"sessions": [{"totalTokens": 50000}]}
        assert _calculate_total_tokens(sessions_data) == 50000

    def test_calculate_total_tokens_multiple_sessions(self):
        """Test calculating tokens for multiple sessions."""
        sessions_data = {
            "sessions": [
                {"totalTokens": 30000},
                {"totalTokens": 20000},
                {"totalTokens": 10000},
            ]
        }
        assert _calculate_total_tokens(sessions_data) == 60000

    def test_calculate_total_tokens_empty_sessions(self):
        """Test calculating tokens with no sessions."""
        sessions_data = {"sessions": []}
        assert _calculate_total_tokens(sessions_data) == 0

    def test_calculate_total_tokens_missing_field(self):
        """Test calculating tokens with missing totalTokens field."""
        sessions_data = {
            "sessions": [
                {"totalTokens": 30000},
                {},  # Missing totalTokens
                {"totalTokens": 10000},
            ]
        }
        assert _calculate_total_tokens(sessions_data) == 40000

    def test_calculate_total_tokens_missing_sessions_key(self):
        """Test calculating tokens with missing sessions key."""
        sessions_data = {}
        assert _calculate_total_tokens(sessions_data) == 0


class TestGatewayStatusWidget:
    """Tests for the GatewayStatusWidget."""

    @pytest.fixture
    def mock_collectors(self):
        """Mock the gateway and sessions collectors."""
        with (
            patch("openclaw_dash.widgets.gateway_status.gateway") as mock_gateway,
            patch("openclaw_dash.widgets.gateway_status.sessions") as mock_sessions,
        ):
            yield mock_gateway, mock_sessions

    def test_widget_creation(self):
        """Test widget can be created."""
        widget = GatewayStatusWidget()
        assert widget is not None

    def test_widget_creation_with_params(self):
        """Test widget creation with custom parameters."""
        widget = GatewayStatusWidget(
            refresh_interval=5.0,
            gateway_url="localhost:8080",
        )
        assert widget.refresh_interval == 5.0
        assert widget.gateway_url == "localhost:8080"

    def test_widget_default_refresh_interval(self):
        """Test widget has default 10 second refresh interval."""
        widget = GatewayStatusWidget()
        assert widget.refresh_interval == 10.0

    def test_widget_handles_healthy_gateway(self, mock_collectors):
        """Test widget handles healthy gateway data."""
        mock_gateway, mock_sessions = mock_collectors
        mock_gateway.collect.return_value = {
            "healthy": True,
            "default_model": "claude-sonnet-4-20250514",
            "url": "localhost:18789",
        }
        mock_sessions.collect.return_value = {
            "sessions": [{"totalTokens": 50000}],
            "active": 2,
            "total": 3,
        }

        widget = GatewayStatusWidget()
        assert widget is not None

    def test_widget_handles_unhealthy_gateway(self, mock_collectors):
        """Test widget handles disconnected gateway."""
        mock_gateway, mock_sessions = mock_collectors
        mock_gateway.collect.return_value = {
            "healthy": False,
            "error": "Cannot connect to gateway",
            "_hint": "Try: openclaw gateway start",
        }
        mock_sessions.collect.return_value = {
            "sessions": [],
            "active": 0,
            "total": 0,
        }

        widget = GatewayStatusWidget()
        assert widget is not None

    def test_widget_handles_empty_sessions(self, mock_collectors):
        """Test widget handles empty sessions."""
        mock_gateway, mock_sessions = mock_collectors
        mock_gateway.collect.return_value = {
            "healthy": True,
            "default_model": "claude-sonnet-4-20250514",
        }
        mock_sessions.collect.return_value = {
            "sessions": [],
            "active": 0,
            "total": 0,
        }

        widget = GatewayStatusWidget()
        assert widget is not None


class TestGatewayStatusSummary:
    """Tests for the GatewayStatusSummary widget."""

    @pytest.fixture
    def mock_collectors(self):
        """Mock the gateway and sessions collectors."""
        with (
            patch("openclaw_dash.widgets.gateway_status.gateway") as mock_gateway,
            patch("openclaw_dash.widgets.gateway_status.sessions") as mock_sessions,
        ):
            yield mock_gateway, mock_sessions

    def test_summary_creation(self):
        """Test summary widget can be created."""
        widget = GatewayStatusSummary()
        assert widget is not None

    def test_summary_creation_with_params(self):
        """Test summary creation with custom parameters."""
        widget = GatewayStatusSummary(refresh_interval=5.0)
        assert widget.refresh_interval == 5.0

    def test_summary_handles_healthy_gateway(self, mock_collectors):
        """Test summary handles healthy gateway."""
        mock_gateway, mock_sessions = mock_collectors
        mock_gateway.collect.return_value = {
            "healthy": True,
            "default_model": "claude-sonnet-4-20250514",
        }
        mock_sessions.collect.return_value = {
            "sessions": [{"totalTokens": 50000}],
            "active": 2,
            "total": 3,
        }

        widget = GatewayStatusSummary()
        assert widget is not None

    def test_summary_handles_offline_gateway(self, mock_collectors):
        """Test summary handles offline gateway."""
        mock_gateway, mock_sessions = mock_collectors
        mock_gateway.collect.return_value = {
            "healthy": False,
            "error": "Gateway not running",
        }
        mock_sessions.collect.return_value = {
            "sessions": [],
            "active": 0,
            "total": 0,
        }

        widget = GatewayStatusSummary()
        assert widget is not None


class TestAmberColors:
    """Tests for amber color constants."""

    def test_amber_colors_defined(self):
        """Test amber colors are properly defined."""
        assert AMBER == "#FFB000"
        assert AMBER_DIM == "#CC8800"
        assert AMBER_BRIGHT == "#FFD54F"

    def test_amber_colors_are_hex(self):
        """Test amber colors are valid hex codes."""
        for color in [AMBER, AMBER_DIM, AMBER_BRIGHT]:
            assert color.startswith("#")
            assert len(color) == 7
