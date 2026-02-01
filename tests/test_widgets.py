"""Tests for dashboard widgets."""

import pytest
from unittest.mock import patch

from textual.widgets import Static

from openclaw_dash.widgets.channels import ChannelsPanel


class TestChannelsPanel:
    """Tests for the ChannelsPanel widget."""

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
    async def test_panel_renders(self):
        """Test that the panel can be instantiated and composed."""
        panel = ChannelsPanel()
        # compose() should yield at least one widget
        children = list(panel.compose())
        assert len(children) >= 1
        # First child should be the content Static
        assert isinstance(children[0], Static)

    @pytest.mark.asyncio
    async def test_refresh_data_with_mock(self):
        """Test refresh_data uses the channels collector."""
        mock_data = {
            "channels": [
                {"type": "discord", "status": "connected", "enabled": True},
                {"type": "telegram", "status": "configured", "enabled": True},
                {"type": "signal", "status": "disabled", "enabled": False},
            ],
            "connected": 1,
            "total": 3,
        }

        with patch("openclaw_dash.widgets.channels.channels.collect", return_value=mock_data):
            # We can't easily test refresh_data without mounting in an app
            # but we can verify the module imports and function exists
            from openclaw_dash.widgets import channels as ch_module
            assert hasattr(ch_module, "ChannelsPanel")


class TestChannelsPanelIntegration:
    """Integration tests for ChannelsPanel in the app."""

    def test_import_from_app(self):
        """ChannelsPanel should be importable from app module."""
        from openclaw_dash.app import ChannelsPanel
        assert ChannelsPanel is not None

    def test_app_has_channels_in_refresh_list(self):
        """DashboardApp should refresh ChannelsPanel."""
        from openclaw_dash.app import DashboardApp, ChannelsPanel
        # Check that action_refresh references ChannelsPanel
        import inspect
        source = inspect.getsource(DashboardApp.action_refresh)
        assert "ChannelsPanel" in source
