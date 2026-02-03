"""Tests for data collectors."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from openclaw_dash.collectors import activity, channels, cron, gateway, repos, sessions


class TestGatewayCollector:
    def test_collect_returns_dict(self):
        result = gateway.collect()
        assert isinstance(result, dict)
        assert "collected_at" in result
        assert "healthy" in result

    def test_healthy_is_bool(self):
        result = gateway.collect()
        assert isinstance(result["healthy"], bool)

    def test_collect_with_demo_mode(self):
        """Gateway collector returns mock data in demo mode."""
        with patch("openclaw_dash.collectors.gateway.is_demo_mode", return_value=True):
            with patch(
                "openclaw_dash.collectors.gateway.mock_gateway_status",
                return_value={"healthy": True, "mode": "demo"},
            ):
                result = gateway.collect()
                assert result["healthy"] is True
                assert result.get("mode") == "demo"

    def test_collect_fallback_to_http_health(self):
        """Gateway falls back to HTTP health check when CLI unavailable."""
        with patch("openclaw_dash.collectors.gateway.is_demo_mode", return_value=False):
            with patch(
                "openclaw_dash.collectors.gateway.get_openclaw_status", return_value=None
            ):
                mock_response = MagicMock()
                mock_response.status_code = 200
                with patch("httpx.get", return_value=mock_response):
                    result = gateway.collect()
                    assert result["healthy"] is True

    def test_collect_returns_unhealthy_on_failure(self):
        """Gateway returns unhealthy when all methods fail."""
        with patch("openclaw_dash.collectors.gateway.is_demo_mode", return_value=False):
            with patch(
                "openclaw_dash.collectors.gateway.get_openclaw_status", return_value=None
            ):
                with patch("httpx.get", side_effect=Exception("Connection refused")):
                    result = gateway.collect()
                    assert result["healthy"] is False
                    assert "error" in result


class TestSessionsCollector:
    def test_collect_returns_dict(self):
        result = sessions.collect()
        assert isinstance(result, dict)
        assert "sessions" in result
        assert isinstance(result["sessions"], list)

    def test_has_counts(self):
        result = sessions.collect()
        assert "total" in result
        assert "active" in result


class TestCronCollector:
    def test_collect_returns_dict(self):
        result = cron.collect()
        assert isinstance(result, dict)
        assert "jobs" in result


class TestReposCollector:
    def test_collect_returns_dict(self):
        result = repos.collect()
        assert isinstance(result, dict)
        assert "repos" in result

    def test_custom_repos_list(self):
        result = repos.collect(repos=["nonexistent-xyz-123"])
        assert result["total"] == 0


class TestActivityCollector:
    def test_collect_returns_dict(self):
        result = activity.collect()
        assert isinstance(result, dict)
        assert "current_task" in result
        assert "recent" in result


class TestChannelsCollector:
    def test_collect_returns_dict(self):
        result = channels.collect()
        assert isinstance(result, dict)
        assert "channels" in result
        assert "connected" in result
        assert "total" in result

    def test_channels_is_list(self):
        result = channels.collect()
        assert isinstance(result["channels"], list)

    def test_get_channel_icon(self):
        assert channels.get_channel_icon("discord") == "🎮"
        assert channels.get_channel_icon("telegram") == "✈️"
        assert channels.get_channel_icon("unknown") == "📱"

    def test_get_status_icon(self):
        assert channels.get_status_icon("connected") == "✓"
        assert channels.get_status_icon("disabled") == "—"

    def test_get_channel_icon_all_types(self):
        """Test all known channel type icons."""
        assert channels.get_channel_icon("signal") == "🔒"
        assert channels.get_channel_icon("slack") == "💼"
        assert channels.get_channel_icon("whatsapp") == "💬"
        assert channels.get_channel_icon("imessage") == "🍎"

    def test_get_status_icon_all_types(self):
        """Test all known status icons."""
        assert channels.get_status_icon("configured") == "○"
        assert channels.get_status_icon("error") == "✗"
        assert channels.get_status_icon("unknown_status") == "?"

    def test_collected_at_is_iso_format(self):
        """Verify collected_at timestamp is valid ISO format."""
        result = channels.collect()
        # Should not raise - valid ISO format
        datetime.fromisoformat(result["collected_at"])

    def test_counts_are_non_negative(self):
        """Channel counts should never be negative."""
        result = channels.collect()
        assert result["connected"] >= 0
        assert result["total"] >= 0
        assert result["connected"] <= result["total"]


class TestActivityCollectorFunctions:
    """Test activity collector helper functions."""

    def test_set_current_task(self, tmp_path, monkeypatch):
        """Test setting current task writes to activity log."""
        # Point to temp directory
        mock_workspace = tmp_path / ".openclaw" / "workspace"
        mock_workspace.mkdir(parents=True)
        monkeypatch.setattr(activity, "WORKSPACE", mock_workspace)
        monkeypatch.setattr(activity, "ACTIVITY_LOG", mock_workspace / "memory" / "activity.json")

        activity.set_current_task("Testing the dashboard")

        # Verify file was created and contains task
        import json

        log_file = mock_workspace / "memory" / "activity.json"
        assert log_file.exists()
        data = json.loads(log_file.read_text())
        assert data["current_task"] == "Testing the dashboard"

    def test_log_activity(self, tmp_path, monkeypatch):
        """Test logging activity appends to recent list."""
        mock_workspace = tmp_path / ".openclaw" / "workspace"
        mock_workspace.mkdir(parents=True)
        monkeypatch.setattr(activity, "WORKSPACE", mock_workspace)
        monkeypatch.setattr(activity, "ACTIVITY_LOG", mock_workspace / "memory" / "activity.json")

        activity.log_activity("First action")
        activity.log_activity("Second action")

        import json

        log_file = mock_workspace / "memory" / "activity.json"
        data = json.loads(log_file.read_text())
        assert len(data["recent"]) == 2
        assert "First action" in data["recent"][0]["action"]
        assert "Second action" in data["recent"][1]["action"]
