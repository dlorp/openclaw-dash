"""Tests for the notifications module."""

from unittest.mock import MagicMock

import pytest

from openclaw_dash.widgets.notifications import (
    ICONS,
    TIMEOUTS,
    NotificationLevel,
    notify,
    notify_error,
    notify_info,
    notify_panel_error,
    notify_refresh,
    notify_success,
    notify_theme_change,
    notify_warning,
)


@pytest.fixture
def mock_app():
    """Create a mock app with notify method."""
    app = MagicMock()
    app.notify = MagicMock()
    return app


class TestNotificationLevel:
    """Tests for NotificationLevel enum."""

    def test_info_level(self):
        assert NotificationLevel.INFO.value == "information"

    def test_warning_level(self):
        assert NotificationLevel.WARNING.value == "warning"

    def test_error_level(self):
        assert NotificationLevel.ERROR.value == "error"

    def test_all_levels_defined(self):
        assert len(NotificationLevel) == 3


class TestNotifyFunction:
    """Tests for the base notify function."""

    def test_notify_calls_app_notify(self, mock_app):
        notify(mock_app, "Test message")
        mock_app.notify.assert_called_once()

    def test_notify_includes_icon(self, mock_app):
        notify(mock_app, "Test", NotificationLevel.INFO)
        call_args = mock_app.notify.call_args
        assert ICONS[NotificationLevel.INFO] in call_args[0][0]

    def test_notify_uses_default_timeout(self, mock_app):
        notify(mock_app, "Test", NotificationLevel.WARNING)
        call_args = mock_app.notify.call_args
        assert call_args[1]["timeout"] == TIMEOUTS[NotificationLevel.WARNING]

    def test_notify_custom_timeout(self, mock_app):
        notify(mock_app, "Test", timeout=5.0)
        call_args = mock_app.notify.call_args
        assert call_args[1]["timeout"] == 5.0

    def test_notify_severity(self, mock_app):
        notify(mock_app, "Test", NotificationLevel.ERROR)
        call_args = mock_app.notify.call_args
        assert call_args[1]["severity"] == "error"


class TestHelperFunctions:
    """Tests for convenience notification functions."""

    def test_notify_info(self, mock_app):
        notify_info(mock_app, "Info message")
        mock_app.notify.assert_called_once()
        call_args = mock_app.notify.call_args
        assert "Info message" in call_args[0][0]
        assert call_args[1]["severity"] == "information"

    def test_notify_success(self, mock_app):
        notify_success(mock_app, "Success!")
        mock_app.notify.assert_called_once()
        call_args = mock_app.notify.call_args
        assert "Success!" in call_args[0][0]
        # Success uses INFO level
        assert call_args[1]["severity"] == "information"

    def test_notify_warning(self, mock_app):
        notify_warning(mock_app, "Warning!")
        mock_app.notify.assert_called_once()
        call_args = mock_app.notify.call_args
        assert "Warning!" in call_args[0][0]
        assert call_args[1]["severity"] == "warning"

    def test_notify_error(self, mock_app):
        notify_error(mock_app, "Error!")
        mock_app.notify.assert_called_once()
        call_args = mock_app.notify.call_args
        assert "Error!" in call_args[0][0]
        assert call_args[1]["severity"] == "error"


class TestSpecializedNotifications:
    """Tests for specialized notification functions."""

    def test_notify_refresh_with_count(self, mock_app):
        notify_refresh(mock_app, panel_count=5)
        call_args = mock_app.notify.call_args
        assert "5 panels" in call_args[0][0]

    def test_notify_refresh_without_count(self, mock_app):
        notify_refresh(mock_app)
        call_args = mock_app.notify.call_args
        assert "Refreshed" in call_args[0][0]

    def test_notify_theme_change(self, mock_app):
        notify_theme_change(mock_app, "dark")
        call_args = mock_app.notify.call_args
        assert "Theme: dark" in call_args[0][0]

    def test_notify_panel_error(self, mock_app):
        notify_panel_error(mock_app, "GatewayPanel", "Connection failed")
        call_args = mock_app.notify.call_args
        assert "GatewayPanel" in call_args[0][0]
        assert "Connection failed" in call_args[0][0]
        assert call_args[1]["severity"] == "error"


class TestTimeouts:
    """Tests for notification timeouts."""

    def test_info_timeout(self):
        assert TIMEOUTS[NotificationLevel.INFO] == 1.5

    def test_warning_timeout(self):
        assert TIMEOUTS[NotificationLevel.WARNING] == 3.0

    def test_error_timeout(self):
        assert TIMEOUTS[NotificationLevel.ERROR] == 5.0


class TestIcons:
    """Tests for notification icons."""

    def test_all_levels_have_icons(self):
        for level in NotificationLevel:
            assert level in ICONS
            assert ICONS[level] != ""
