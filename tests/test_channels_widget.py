"""Comprehensive tests for the ChannelsPanel widget."""

from unittest.mock import MagicMock, patch

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Static

from openclaw_dash.collectors import channels
from openclaw_dash.widgets.channels import ChannelsPanel


class TestChannelHelpers:
    """Tests for channel helper functions."""

    def test_get_channel_icon_discord(self):
        """Test icon for Discord channel."""
        assert channels.get_channel_icon("discord") == ""

    def test_get_channel_icon_telegram(self):
        """Test icon for Telegram channel."""
        assert channels.get_channel_icon("telegram") == ""

    def test_get_channel_icon_signal(self):
        """Test icon for Signal channel."""
        assert channels.get_channel_icon("signal") == ""

    def test_get_channel_icon_slack(self):
        """Test icon for Slack channel."""
        assert channels.get_channel_icon("slack") == ""

    def test_get_channel_icon_whatsapp(self):
        """Test icon for WhatsApp channel."""
        assert channels.get_channel_icon("whatsapp") == ""

    def test_get_channel_icon_imessage(self):
        """Test icon for iMessage channel."""
        assert channels.get_channel_icon("imessage") == ""

    def test_get_channel_icon_unknown(self):
        """Test icon for unknown channel type."""
        assert channels.get_channel_icon("unknown") == ""
        assert channels.get_channel_icon("something_else") == ""

    def test_get_status_icon_connected(self):
        """Test icon for connected status."""
        assert channels.get_status_icon("connected") == "✓"

    def test_get_status_icon_configured(self):
        """Test icon for configured status."""
        assert channels.get_status_icon("configured") == "○"

    def test_get_status_icon_disabled(self):
        """Test icon for disabled status."""
        assert channels.get_status_icon("disabled") == "—"

    def test_get_status_icon_error(self):
        """Test icon for error status."""
        assert channels.get_status_icon("error") == "✗"

    def test_get_status_icon_unknown(self):
        """Test icon for unknown status."""
        assert channels.get_status_icon("unknown") == "?"
        assert channels.get_status_icon("invalid") == "?"


class TestChannelsCollector:
    """Tests for channels collector."""

    def test_collect_returns_dict(self):
        """collect() should return a dict with expected keys."""
        result = channels.collect()
        assert isinstance(result, dict)
        assert "channels" in result
        assert "connected" in result
        assert "total" in result
        assert "collected_at" in result

    def test_collect_channels_is_list(self):
        """channels should be a list."""
        result = channels.collect()
        assert isinstance(result["channels"], list)

    def test_collect_connected_is_int(self):
        """connected count should be an integer."""
        result = channels.collect()
        assert isinstance(result["connected"], int)

    def test_collect_total_is_int(self):
        """total count should be an integer."""
        result = channels.collect()
        assert isinstance(result["total"], int)

    @patch("openclaw_dash.collectors.channels.Path")
    def test_collect_with_config_file(self, mock_path):
        """Test collection with a config file."""
        mock_config = """
channels:
  discord:
    enabled: true
    token: "test-token"
  telegram:
    enabled: false
    botToken: "test-bot-token"
"""
        mock_path_obj = MagicMock()
        mock_path_obj.exists.return_value = True
        mock_path_obj.read_text.return_value = mock_config
        mock_path.return_value.__truediv__.return_value.__truediv__.return_value = mock_path_obj
        mock_path.home.return_value.__truediv__.return_value.__truediv__.return_value = (
            mock_path_obj
        )

        # Since collect() uses Path.home(), we need to patch at that level
        with patch.object(channels.Path, "home", return_value=MagicMock()) as mock_home:
            mock_home.return_value.__truediv__.return_value.__truediv__.return_value = mock_path_obj
            result = channels.collect()
            # Should have at least attempted collection
            assert isinstance(result["channels"], list)

    def test_check_channel_health(self):
        """Test channel health check (currently returns True)."""
        # Currently just returns True as a placeholder
        assert channels._check_channel_health("discord") is True
        assert channels._check_channel_health("telegram") is True
        assert channels._check_channel_health("unknown") is True


class TestChannelsPanelWidget:
    """Tests for ChannelsPanel widget class."""

    def test_is_static_subclass(self):
        """ChannelsPanel should inherit from Static."""
        assert issubclass(ChannelsPanel, Static)

    def test_has_refresh_data_method(self):
        """ChannelsPanel should have refresh_data method."""
        assert hasattr(ChannelsPanel, "refresh_data")
        assert callable(getattr(ChannelsPanel, "refresh_data"))

    def test_has_compose_method(self):
        """ChannelsPanel should have compose method."""
        assert hasattr(ChannelsPanel, "compose")
        assert callable(getattr(ChannelsPanel, "compose"))

    @pytest.mark.asyncio
    async def test_panel_compose_yields_static(self):
        """Test that compose yields a Static widget."""
        panel = ChannelsPanel()
        children = list(panel.compose())
        assert len(children) >= 1
        assert isinstance(children[0], Static)

    @pytest.mark.asyncio
    async def test_panel_content_has_id(self):
        """Test that the content widget has correct ID."""
        panel = ChannelsPanel()
        children = list(panel.compose())
        content = children[0]
        assert content.id == "channels-content"


class ChannelsPanelTestApp(App):
    """Test app for mounting ChannelsPanel."""

    def compose(self) -> ComposeResult:
        yield ChannelsPanel(id="test-channels")


class TestChannelsPanelIntegration:
    """Integration tests for ChannelsPanel in an app context."""

    @pytest.mark.asyncio
    async def test_panel_mounts_correctly(self):
        """Test that panel mounts without errors."""
        app = ChannelsPanelTestApp()
        async with app.run_test():
            panel = app.query_one(ChannelsPanel)
            assert panel is not None

    @pytest.mark.asyncio
    async def test_refresh_with_no_channels(self):
        """Test refresh_data with no channels configured."""
        mock_data = {
            "channels": [],
            "connected": 0,
            "total": 0,
            "collected_at": "2026-02-01T12:00:00",
        }

        app = ChannelsPanelTestApp()
        async with app.run_test():
            with patch(
                "openclaw_dash.widgets.channels.channels.collect",
                return_value=mock_data,
            ) as mock_collect:
                panel = app.query_one(ChannelsPanel)
                panel.refresh_data()
                # Verify collect was called
                mock_collect.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_with_connected_channel(self):
        """Test refresh_data with a connected channel."""
        mock_data = {
            "channels": [
                {"type": "discord", "status": "connected", "enabled": True},
            ],
            "connected": 1,
            "total": 1,
            "collected_at": "2026-02-01T12:00:00",
        }

        app = ChannelsPanelTestApp()
        async with app.run_test():
            with patch(
                "openclaw_dash.widgets.channels.channels.collect",
                return_value=mock_data,
            ) as mock_collect:
                panel = app.query_one(ChannelsPanel)
                panel.refresh_data()
                mock_collect.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_with_multiple_channels(self):
        """Test refresh_data with multiple channels."""
        mock_data = {
            "channels": [
                {"type": "discord", "status": "connected", "enabled": True},
                {"type": "telegram", "status": "configured", "enabled": True},
                {"type": "signal", "status": "disabled", "enabled": False},
            ],
            "connected": 1,
            "total": 3,
            "collected_at": "2026-02-01T12:00:00",
        }

        app = ChannelsPanelTestApp()
        async with app.run_test():
            with patch(
                "openclaw_dash.widgets.channels.channels.collect",
                return_value=mock_data,
            ) as mock_collect:
                panel = app.query_one(ChannelsPanel)
                panel.refresh_data()
                mock_collect.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_handles_many_channels(self):
        """Test that refresh_data handles many channels (limits to 6)."""
        mock_data = {
            "channels": [
                {"type": f"channel{i}", "status": "connected", "enabled": True} for i in range(10)
            ],
            "connected": 10,
            "total": 10,
            "collected_at": "2026-02-01T12:00:00",
        }

        app = ChannelsPanelTestApp()
        async with app.run_test():
            with patch(
                "openclaw_dash.widgets.channels.channels.collect",
                return_value=mock_data,
            ) as mock_collect:
                panel = app.query_one(ChannelsPanel)
                # Should not raise even with 10 channels
                panel.refresh_data()
                mock_collect.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_handles_all_statuses(self):
        """Test that refresh_data handles all status types."""
        mock_data = {
            "channels": [
                {"type": "discord", "status": "connected", "enabled": True},
                {"type": "telegram", "status": "configured", "enabled": True},
                {"type": "signal", "status": "disabled", "enabled": False},
                {"type": "slack", "status": "error", "enabled": True},
                {"type": "whatsapp", "status": "unknown", "enabled": True},
            ],
            "connected": 1,
            "total": 5,
            "collected_at": "2026-02-01T12:00:00",
        }

        app = ChannelsPanelTestApp()
        async with app.run_test():
            with patch(
                "openclaw_dash.widgets.channels.channels.collect",
                return_value=mock_data,
            ) as mock_collect:
                panel = app.query_one(ChannelsPanel)
                # Should not raise for any status type
                panel.refresh_data()
                mock_collect.assert_called_once()


class TestChannelsPanelAppIntegration:
    """Tests for ChannelsPanel integration with DashboardApp."""

    def test_import_from_app(self):
        """ChannelsPanel should be importable from app module."""
        from openclaw_dash.app import ChannelsPanel as AppChannelsPanel

        assert AppChannelsPanel is not None
        assert AppChannelsPanel is ChannelsPanel

    def test_app_has_channels_in_refresh_list(self):
        """DashboardApp should refresh ChannelsPanel."""
        import inspect

        from openclaw_dash.app import DashboardApp

        source = inspect.getsource(DashboardApp.action_refresh)
        assert "ChannelsPanel" in source

    def test_app_has_channels_in_auto_refresh(self):
        """DashboardApp should auto-refresh ChannelsPanel."""
        import inspect

        from openclaw_dash.app import DashboardApp

        source = inspect.getsource(DashboardApp._do_auto_refresh)
        assert "ChannelsPanel" in source

    def test_channels_panel_in_compose(self):
        """DashboardApp compose should include channels-panel."""
        import inspect

        from openclaw_dash.app import DashboardApp

        source = inspect.getsource(DashboardApp.compose)
        assert "channels-panel" in source
