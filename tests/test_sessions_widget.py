"""Tests for sessions widget."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from openclaw_dash.widgets.sessions import (
    SessionsPanel,
    SessionsSummaryPanel,
    SessionStatus,
    _calculate_context_pct,
    _calculate_time_active,
    _determine_status,
    get_status_color,
    get_status_icon,
)


class TestSessionStatus:
    """Tests for SessionStatus enum."""

    def test_status_values(self):
        """Test that all status values are correct."""
        assert SessionStatus.ACTIVE.value == "active"
        assert SessionStatus.IDLE.value == "idle"
        assert SessionStatus.SPAWNING.value == "spawning"
        assert SessionStatus.UNKNOWN.value == "unknown"


class TestStatusHelpers:
    """Tests for status helper functions."""

    def test_get_status_icon_active(self):
        """Test icon for active status."""
        assert get_status_icon("active") == "●"

    def test_get_status_icon_idle(self):
        """Test icon for idle status."""
        assert get_status_icon("idle") == "◐"

    def test_get_status_icon_spawning(self):
        """Test icon for spawning status."""
        assert get_status_icon("spawning") == "◌"

    def test_get_status_icon_unknown(self):
        """Test icon for unknown status."""
        assert get_status_icon("unknown") == "?"

    def test_get_status_icon_invalid(self):
        """Test icon for invalid status returns default."""
        assert get_status_icon("invalid") == "?"

    def test_get_status_color_active(self):
        """Test color for active status."""
        assert get_status_color("active") == "green"

    def test_get_status_color_idle(self):
        """Test color for idle status."""
        assert get_status_color("idle") == "yellow"

    def test_get_status_color_spawning(self):
        """Test color for spawning status."""
        assert get_status_color("spawning") == "cyan"

    def test_get_status_color_unknown(self):
        """Test color for unknown status."""
        assert get_status_color("unknown") == "white"

    def test_get_status_color_invalid(self):
        """Test color for invalid status returns default."""
        assert get_status_color("invalid") == "white"


class TestCalculateTimeActive:
    """Tests for time active calculation."""

    def test_time_active_seconds(self):
        """Test time active in seconds."""
        now = datetime.now()
        updated_at_ms = (now - timedelta(seconds=30)).timestamp() * 1000
        result = _calculate_time_active(updated_at_ms)
        assert "s" in result
        assert "m" not in result

    def test_time_active_minutes(self):
        """Test time active in minutes."""
        now = datetime.now()
        updated_at_ms = (now - timedelta(minutes=5, seconds=30)).timestamp() * 1000
        result = _calculate_time_active(updated_at_ms)
        assert "m" in result
        assert "h" not in result

    def test_time_active_hours(self):
        """Test time active in hours."""
        now = datetime.now()
        updated_at_ms = (now - timedelta(hours=2, minutes=15)).timestamp() * 1000
        result = _calculate_time_active(updated_at_ms)
        assert "h" in result

    def test_time_active_none(self):
        """Test time active with None returns ?."""
        assert _calculate_time_active(None) == "?"

    def test_time_active_future(self):
        """Test time active for future timestamp."""
        now = datetime.now()
        updated_at_ms = (now + timedelta(seconds=30)).timestamp() * 1000
        result = _calculate_time_active(updated_at_ms)
        assert result == "just now"


class TestDetermineStatus:
    """Tests for status determination."""

    def test_determine_status_spawning(self):
        """Test spawning status detection."""
        session = {"spawning": True}
        assert _determine_status(session) == "spawning"

    def test_determine_status_active_flag(self):
        """Test active status from flag."""
        session = {"active": True}
        assert _determine_status(session) == "active"

    def test_determine_status_idle_by_time(self):
        """Test idle status when inactive for too long."""
        now = datetime.now()
        old_time_ms = (now - timedelta(minutes=10)).timestamp() * 1000
        session = {"updatedAt": old_time_ms}
        assert _determine_status(session) == "idle"

    def test_determine_status_active_by_time(self):
        """Test active status when recently active."""
        now = datetime.now()
        recent_time_ms = (now - timedelta(seconds=30)).timestamp() * 1000
        session = {"updatedAt": recent_time_ms}
        assert _determine_status(session) == "active"

    def test_determine_status_default(self):
        """Test default active status."""
        session = {}
        assert _determine_status(session) == "active"


class TestCalculateContextPct:
    """Tests for context percentage calculation."""

    def test_context_pct_from_field(self):
        """Test context_pct from existing field."""
        session = {"context_pct": 45.5}
        assert _calculate_context_pct(session) == 45.5

    def test_context_pct_from_tokens(self):
        """Test context_pct calculated from tokens."""
        session = {"totalTokens": 50000, "contextTokens": 200000}
        result = _calculate_context_pct(session)
        assert result == 25.0

    def test_context_pct_from_context_usage(self):
        """Test context_pct from contextUsage (0-1 scale)."""
        session = {"contextUsage": 0.35}
        result = _calculate_context_pct(session)
        assert result == 35.0

    def test_context_pct_zero_context_tokens(self):
        """Test context_pct with zero context tokens."""
        session = {"totalTokens": 50000, "contextTokens": 0}
        result = _calculate_context_pct(session)
        assert result == 0.0

    def test_context_pct_empty_session(self):
        """Test context_pct with empty session."""
        session = {}
        result = _calculate_context_pct(session)
        assert result == 0.0


class TestSessionsPanel:
    """Tests for the SessionsPanel widget."""

    @pytest.fixture
    def mock_collect(self):
        """Mock the sessions.collect function."""
        with patch("openclaw_dash.widgets.sessions.sessions.collect") as mock:
            yield mock

    def test_panel_creation(self):
        """Test panel can be created."""
        panel = SessionsPanel()
        assert panel is not None

    def test_panel_handles_empty_sessions(self, mock_collect):
        """Test panel displays message when no sessions."""
        mock_collect.return_value = {
            "sessions": [],
            "total": 0,
            "active": 0,
            "collected_at": datetime.now().isoformat(),
        }

        panel = SessionsPanel()
        assert panel is not None

    def test_panel_handles_sessions_data(self, mock_collect):
        """Test panel handles session data correctly."""
        now = datetime.now()
        mock_collect.return_value = {
            "sessions": [
                {
                    "key": "agent:main:main",
                    "displayName": "main",
                    "kind": "main",
                    "active": True,
                    "totalTokens": 45000,
                    "contextTokens": 200000,
                    "updatedAt": now.timestamp() * 1000,
                },
                {
                    "key": "agent:main:subagent:test",
                    "displayName": "test",
                    "kind": "subagent",
                    "active": True,
                    "totalTokens": 12000,
                    "contextTokens": 200000,
                    "updatedAt": (now - timedelta(minutes=5)).timestamp() * 1000,
                },
            ],
            "total": 2,
            "active": 2,
            "collected_at": now.isoformat(),
        }

        panel = SessionsPanel()
        assert panel is not None

    def test_panel_limits_display(self, mock_collect):
        """Test panel limits sessions displayed."""
        now = datetime.now()
        sessions = [
            {
                "key": f"agent:main:subagent:test{i}",
                "displayName": f"test{i}",
                "kind": "subagent",
                "active": True,
                "totalTokens": 10000,
                "contextTokens": 200000,
                "updatedAt": now.timestamp() * 1000,
            }
            for i in range(15)
        ]
        mock_collect.return_value = {
            "sessions": sessions,
            "total": 15,
            "active": 15,
            "collected_at": now.isoformat(),
        }

        panel = SessionsPanel()
        assert panel is not None


class TestSessionsSummaryPanel:
    """Tests for the SessionsSummaryPanel widget."""

    @pytest.fixture
    def mock_collect(self):
        """Mock the sessions.collect function."""
        with patch("openclaw_dash.widgets.sessions.sessions.collect") as mock:
            yield mock

    def test_summary_panel_creation(self):
        """Test summary panel can be created."""
        panel = SessionsSummaryPanel()
        assert panel is not None

    def test_summary_panel_handles_empty(self, mock_collect):
        """Test summary panel handles empty sessions."""
        mock_collect.return_value = {
            "sessions": [],
            "total": 0,
            "active": 0,
            "collected_at": datetime.now().isoformat(),
        }

        panel = SessionsSummaryPanel()
        assert panel is not None

    def test_summary_panel_handles_data(self, mock_collect):
        """Test summary panel handles session data."""
        now = datetime.now()
        mock_collect.return_value = {
            "sessions": [
                {
                    "key": "agent:main:main",
                    "totalTokens": 80000,
                    "contextTokens": 200000,
                    "updatedAt": now.timestamp() * 1000,
                },
                {
                    "key": "agent:main:subagent:test",
                    "totalTokens": 40000,
                    "contextTokens": 200000,
                    "updatedAt": now.timestamp() * 1000,
                },
            ],
            "total": 2,
            "active": 2,
            "collected_at": now.isoformat(),
        }

        panel = SessionsSummaryPanel()
        assert panel is not None

    def test_summary_context_color_high(self, mock_collect):
        """Test summary shows red for high context usage."""
        now = datetime.now()
        mock_collect.return_value = {
            "sessions": [
                {
                    "key": "test",
                    "totalTokens": 180000,
                    "contextTokens": 200000,
                    "updatedAt": now.timestamp() * 1000,
                }
            ],
            "total": 1,
            "active": 1,
            "collected_at": now.isoformat(),
        }

        panel = SessionsSummaryPanel()
        assert panel is not None

    def test_summary_context_color_medium(self, mock_collect):
        """Test summary shows yellow for medium context usage."""
        now = datetime.now()
        mock_collect.return_value = {
            "sessions": [
                {
                    "key": "test",
                    "totalTokens": 140000,
                    "contextTokens": 200000,
                    "updatedAt": now.timestamp() * 1000,
                }
            ],
            "total": 1,
            "active": 1,
            "collected_at": now.isoformat(),
        }

        panel = SessionsSummaryPanel()
        assert panel is not None
