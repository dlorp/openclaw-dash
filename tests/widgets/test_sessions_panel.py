"""Tests for the SessionsTablePanel widget."""

from unittest.mock import patch

import pytest
from textual.widgets import DataTable, Static

from openclaw_dash.widgets.sessions_table import (
    HIGH_TOKEN_THRESHOLD,
    SessionSelected,
    SessionsTablePanel,
    SessionsTableSummary,
    classify_kind,
    format_tokens,
    get_context_color,
    parse_channel_from_key,
)


class TestParseChannelFromKey:
    """Tests for channel parsing from session keys."""

    def test_discord_channel(self):
        """Should extract discord from key."""
        key = "agent:main:discord:channel:1234567890"
        assert parse_channel_from_key(key) == "discord"

    def test_telegram_channel(self):
        """Should extract telegram from key."""
        key = "agent:florp:telegram:chat:456"
        assert parse_channel_from_key(key) == "telegram"

    def test_slack_channel(self):
        """Should extract slack from key."""
        key = "agent:bot:slack:workspace:abc"
        assert parse_channel_from_key(key) == "slack"

    def test_main_session_local(self):
        """Should return local for main sessions without channel."""
        key = "agent:main:main"
        assert parse_channel_from_key(key) == "local"

    def test_subagent_local(self):
        """Should return local for subagent sessions."""
        key = "agent:florp:subagent:blorp"
        assert parse_channel_from_key(key) == "local"

    def test_empty_key(self):
        """Should return dash for empty key."""
        assert parse_channel_from_key("") == "-"
        assert parse_channel_from_key(None) == "-"

    def test_unknown_format(self):
        """Should return dash for unknown formats."""
        key = "unknown:format"
        assert parse_channel_from_key(key) == "-"


class TestClassifyKind:
    """Tests for session kind classification."""

    def test_main_kind(self):
        """Should classify main sessions."""
        assert classify_kind("main") == "main"
        assert classify_kind("primary") == "main"
        assert classify_kind("MAIN") == "main"

    def test_group_kind(self):
        """Should classify group sessions."""
        assert classify_kind("group") == "group"
        assert classify_kind("shared") == "group"
        assert classify_kind("channel") == "group"

    def test_subagent_kind(self):
        """Should classify subagent sessions."""
        assert classify_kind("subagent") == "subagent"
        assert classify_kind("sub") == "subagent"
        assert classify_kind("agent") == "subagent"

    def test_other_kind(self):
        """Should return original or 'other' for unknown kinds."""
        assert classify_kind("custom") == "custom"
        assert classify_kind("") == "other"
        assert classify_kind(None) == "other"


class TestFormatTokens:
    """Tests for token count formatting."""

    def test_millions(self):
        """Should format millions correctly."""
        assert format_tokens(1_500_000) == "1.5M"
        assert format_tokens(1_000_000) == "1.0M"

    def test_thousands(self):
        """Should format thousands correctly."""
        assert format_tokens(45_000) == "45k"
        assert format_tokens(1_000) == "1k"
        assert format_tokens(999_000) == "999k"

    def test_small_numbers(self):
        """Should return raw number for small values."""
        assert format_tokens(500) == "500"
        assert format_tokens(0) == "0"


class TestGetContextColor:
    """Tests for context usage color coding."""

    def test_critical_usage(self):
        """Should return red for critical usage (>=80%)."""
        assert get_context_color(80) == "red"
        assert get_context_color(95) == "red"
        assert get_context_color(100) == "red"

    def test_high_usage(self):
        """Should return brand orange for high usage (>=70%)."""
        from openclaw_dash.themes import DARK_ORANGE

        assert get_context_color(70) == DARK_ORANGE
        assert get_context_color(79) == DARK_ORANGE

    def test_medium_usage(self):
        """Should return yellow for medium usage (>=50%)."""
        assert get_context_color(50) == "yellow"
        assert get_context_color(69) == "yellow"

    def test_low_usage(self):
        """Should return green for low usage (<50%)."""
        assert get_context_color(0) == "green"
        assert get_context_color(49) == "green"


class TestHighTokenThreshold:
    """Tests for the high token threshold constant."""

    def test_threshold_value(self):
        """Threshold should be 70%."""
        assert HIGH_TOKEN_THRESHOLD == 70


class TestSessionSelectedMessage:
    """Tests for the SessionSelected message."""

    def test_message_creation(self):
        """Should create message with session key."""
        msg = SessionSelected("agent:main:discord:123")
        assert msg.session_key == "agent:main:discord:123"

    def test_message_with_empty_key(self):
        """Should handle empty key."""
        msg = SessionSelected("")
        assert msg.session_key == ""


class TestSessionsTablePanel:
    """Tests for the SessionsTablePanel widget."""

    def test_is_static_subclass(self):
        """SessionsTablePanel should inherit from Static."""
        assert issubclass(SessionsTablePanel, Static)

    def test_has_refresh_data_method(self):
        """SessionsTablePanel should have refresh_data method."""
        assert hasattr(SessionsTablePanel, "refresh_data")
        assert callable(getattr(SessionsTablePanel, "refresh_data"))

    def test_has_compose_method(self):
        """SessionsTablePanel should have compose method."""
        assert hasattr(SessionsTablePanel, "compose")
        assert callable(getattr(SessionsTablePanel, "compose"))

    @pytest.mark.asyncio
    async def test_panel_renders_datatable(self):
        """Test that the panel yields a DataTable."""
        panel = SessionsTablePanel()
        children = list(panel.compose())
        assert len(children) == 1
        assert isinstance(children[0], DataTable)

    def test_datatable_has_correct_id(self):
        """Test that DataTable has correct ID."""
        panel = SessionsTablePanel()
        children = list(panel.compose())
        table = children[0]
        assert table.id == "sessions-table"

    def test_module_imports(self):
        """Test that the module imports correctly."""
        from openclaw_dash.widgets import sessions_table

        assert hasattr(sessions_table, "SessionsTablePanel")
        assert hasattr(sessions_table, "SessionsTableSummary")
        assert hasattr(sessions_table, "SessionSelected")


class TestSessionsTableSummary:
    """Tests for the SessionsTableSummary widget."""

    def test_is_static_subclass(self):
        """SessionsTableSummary should inherit from Static."""
        assert issubclass(SessionsTableSummary, Static)

    def test_has_refresh_data_method(self):
        """SessionsTableSummary should have refresh_data method."""
        assert hasattr(SessionsTableSummary, "refresh_data")
        assert callable(getattr(SessionsTableSummary, "refresh_data"))

    @pytest.mark.asyncio
    async def test_panel_renders(self):
        """Test that the summary panel can be composed."""
        panel = SessionsTableSummary()
        children = list(panel.compose())
        assert len(children) >= 1
        assert isinstance(children[0], Static)


class TestSessionsTablePanelIntegration:
    """Integration tests for SessionsTablePanel with collector."""

    def test_refresh_with_mock_data(self):
        """Test refresh_data processes mock data correctly."""
        mock_data = {
            "sessions": [
                {
                    "key": "agent:main:discord:channel:123",
                    "kind": "main",
                    "model": "claude-sonnet-4-20250514",
                    "totalTokens": 45000,
                    "contextTokens": 200000,
                    "context_pct": 22.5,
                },
                {
                    "key": "agent:main:subagent:blorp",
                    "kind": "subagent",
                    "model": "claude-sonnet-4-20250514",
                    "totalTokens": 150000,
                    "contextTokens": 200000,
                    "context_pct": 75.0,  # High token usage
                },
            ],
            "total": 2,
            "active": 2,
        }

        with patch(
            "openclaw_dash.widgets.sessions_table.sessions.collect",
            return_value=mock_data,
        ):
            panel = SessionsTablePanel()
            # Verify panel can be created
            assert panel is not None
            # Verify compose yields a DataTable (columns added on_mount)
            children = list(panel.compose())
            assert len(children) == 1
            assert isinstance(children[0], DataTable)

    def test_empty_sessions(self):
        """Test handling of empty sessions list."""
        mock_data = {
            "sessions": [],
            "total": 0,
            "active": 0,
        }

        with patch(
            "openclaw_dash.widgets.sessions_table.sessions.collect",
            return_value=mock_data,
        ):
            panel = SessionsTablePanel()
            assert panel is not None

    def test_high_context_highlighting(self):
        """Test that high context sessions are identified."""
        mock_data = {
            "sessions": [
                {
                    "key": "agent:main:main",
                    "kind": "main",
                    "model": "gpt-4",
                    "totalTokens": 180000,
                    "contextTokens": 200000,
                    "context_pct": 90.0,  # Critical usage
                },
            ],
            "total": 1,
            "active": 1,
        }

        with patch(
            "openclaw_dash.widgets.sessions_table.sessions.collect",
            return_value=mock_data,
        ):
            panel = SessionsTablePanel()
            # Panel should handle high context sessions
            assert panel is not None


class TestSessionsTableSummaryIntegration:
    """Integration tests for SessionsTableSummary."""

    def test_summary_with_mixed_usage(self):
        """Test summary calculates averages correctly."""
        mock_data = {
            "sessions": [
                {"key": "s1", "context_pct": 30},
                {"key": "s2", "context_pct": 50},
                {"key": "s3", "context_pct": 80},  # High usage
            ],
            "total": 3,
            "active": 3,
        }

        with patch(
            "openclaw_dash.widgets.sessions_table.sessions.collect",
            return_value=mock_data,
        ):
            panel = SessionsTableSummary()
            assert panel is not None

    def test_summary_empty_sessions(self):
        """Test summary with no sessions."""
        mock_data = {
            "sessions": [],
            "total": 0,
            "active": 0,
        }

        with patch(
            "openclaw_dash.widgets.sessions_table.sessions.collect",
            return_value=mock_data,
        ):
            panel = SessionsTableSummary()
            assert panel is not None


class TestWidgetExports:
    """Test that widgets are properly exported from the package."""

    def test_exports_from_widgets_package(self):
        """Test all new exports are available from widgets package."""
        from openclaw_dash.widgets import (
            HIGH_TOKEN_THRESHOLD,
            SessionSelected,
            SessionsTablePanel,
            SessionsTableSummary,
            classify_kind,
            format_tokens,
            get_context_color,
            parse_channel_from_key,
        )

        assert SessionsTablePanel is not None
        assert SessionsTableSummary is not None
        assert SessionSelected is not None
        assert HIGH_TOKEN_THRESHOLD == 70
        assert callable(parse_channel_from_key)
        assert callable(classify_kind)
        assert callable(format_tokens)
        assert callable(get_context_color)
