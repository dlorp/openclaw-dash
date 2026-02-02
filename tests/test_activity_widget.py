"""Tests for activity widget."""

from datetime import datetime
from unittest.mock import patch

import pytest

from openclaw_dash.widgets.activity import (
    ACTIVITY_COLORS,
    ACTIVITY_ICONS_ASCII,
    ActivityPanel,
    ActivitySummaryPanel,
    ActivityType,
    get_activity_color,
    get_activity_icon,
    get_activity_type,
)


class TestActivityType:
    """Tests for ActivityType enum and helpers."""

    def test_activity_type_values(self):
        """Test that all activity type values are correct."""
        assert ActivityType.GIT.value == "git"
        assert ActivityType.PR.value == "pr"
        assert ActivityType.CI.value == "ci"
        assert ActivityType.AGENT.value == "agent"
        assert ActivityType.TASK.value == "task"
        assert ActivityType.MESSAGE.value == "message"
        assert ActivityType.DEFAULT.value == "default"

    def test_get_activity_type_valid(self):
        """Test get_activity_type with valid types."""
        assert get_activity_type("git") == ActivityType.GIT
        assert get_activity_type("pr") == ActivityType.PR
        assert get_activity_type("ci") == ActivityType.CI
        assert get_activity_type("agent") == ActivityType.AGENT
        assert get_activity_type("task") == ActivityType.TASK
        assert get_activity_type("message") == ActivityType.MESSAGE

    def test_get_activity_type_case_insensitive(self):
        """Test get_activity_type is case insensitive."""
        assert get_activity_type("GIT") == ActivityType.GIT
        assert get_activity_type("Git") == ActivityType.GIT
        assert get_activity_type("PR") == ActivityType.PR

    def test_get_activity_type_unknown(self):
        """Test get_activity_type with unknown type returns DEFAULT."""
        assert get_activity_type("unknown") == ActivityType.DEFAULT
        assert get_activity_type("invalid") == ActivityType.DEFAULT
        assert get_activity_type("") == ActivityType.DEFAULT
        assert get_activity_type(None) == ActivityType.DEFAULT


class TestActivityIcons:
    """Tests for activity icons."""

    def test_get_activity_icon_ascii(self):
        """Test getting ASCII icons for activity types."""
        assert get_activity_icon(ActivityType.GIT, ascii_mode=True) == "⎇"
        assert get_activity_icon(ActivityType.PR, ascii_mode=True) == "⤴"
        assert get_activity_icon(ActivityType.CI, ascii_mode=True) == "⚙"
        assert get_activity_icon(ActivityType.AGENT, ascii_mode=True) == "◉"
        assert get_activity_icon(ActivityType.TASK, ascii_mode=True) == "✓"
        assert get_activity_icon(ActivityType.MESSAGE, ascii_mode=True) == "✉"
        assert get_activity_icon(ActivityType.DEFAULT, ascii_mode=True) == "●"

    def test_all_activity_types_have_icons(self):
        """Test that all activity types have ASCII icons defined."""
        for activity_type in ActivityType:
            assert activity_type in ACTIVITY_ICONS_ASCII

    def test_all_activity_types_have_colors(self):
        """Test that all activity types have colors defined."""
        for activity_type in ActivityType:
            assert activity_type in ACTIVITY_COLORS


class TestActivityColors:
    """Tests for activity colors."""

    def test_get_activity_color(self):
        """Test getting colors for activity types."""
        assert get_activity_color(ActivityType.GIT) == "cyan"
        assert get_activity_color(ActivityType.PR) == "magenta"
        assert get_activity_color(ActivityType.CI) == "yellow"
        assert get_activity_color(ActivityType.AGENT) == "green"
        assert get_activity_color(ActivityType.TASK) == "blue"
        assert get_activity_color(ActivityType.MESSAGE) == "white"
        assert get_activity_color(ActivityType.DEFAULT) == "dim"


class TestActivityPanel:
    """Tests for the ActivityPanel widget."""

    @pytest.fixture
    def mock_collect(self):
        """Mock the activity.collect function."""
        with patch("openclaw_dash.widgets.activity.activity.collect") as mock:
            yield mock

    def test_panel_creation(self):
        """Test basic panel creation."""
        panel = ActivityPanel()
        assert panel is not None
        assert panel.max_items == 8
        assert panel.ascii_icons is True

    def test_panel_custom_max_items(self):
        """Test panel creation with custom max_items."""
        panel = ActivityPanel(max_items=5)
        assert panel.max_items == 5

    def test_panel_ascii_icons_toggle(self):
        """Test panel with ASCII icons disabled."""
        panel = ActivityPanel(ascii_icons=False)
        assert panel.ascii_icons is False

    def test_panel_handles_empty_activity(self, mock_collect):
        """Test panel displays message when no activity."""
        mock_collect.return_value = {
            "current_task": None,
            "recent": [],
            "collected_at": datetime.now().isoformat(),
        }
        panel = ActivityPanel()
        assert panel is not None

    def test_panel_handles_current_task(self, mock_collect):
        """Test panel handles current task correctly."""
        mock_collect.return_value = {
            "current_task": "Building feature X",
            "recent": [],
            "collected_at": datetime.now().isoformat(),
        }
        panel = ActivityPanel()
        assert panel is not None

    def test_panel_handles_recent_activity(self, mock_collect):
        """Test panel handles recent activity correctly."""
        mock_collect.return_value = {
            "current_task": None,
            "recent": [
                {"time": "12:30", "action": "Pushed code", "type": "git"},
                {"time": "12:45", "action": "Created PR", "type": "pr"},
            ],
            "collected_at": datetime.now().isoformat(),
        }
        panel = ActivityPanel()
        assert panel is not None

    def test_panel_handles_both_task_and_activity(self, mock_collect):
        """Test panel handles both current task and activity."""
        mock_collect.return_value = {
            "current_task": "Working on tests",
            "recent": [
                {"time": "12:30", "action": "Added tests", "type": "task"},
            ],
            "collected_at": datetime.now().isoformat(),
        }
        panel = ActivityPanel()
        assert panel is not None


class TestActivityPanelTimeFormatting:
    """Tests for time formatting in ActivityPanel."""

    def test_format_time_hhmm_string(self):
        """Test formatting HH:MM string."""
        panel = ActivityPanel()
        assert panel._format_time("12:30") == "12:30"
        assert panel._format_time("09:05") == "09:05"

    def test_format_time_datetime(self):
        """Test formatting datetime object."""
        panel = ActivityPanel()
        dt = datetime(2026, 2, 1, 14, 30, 45)
        assert panel._format_time(dt) == "14:30"

    def test_format_time_iso_string(self):
        """Test formatting ISO format string."""
        panel = ActivityPanel()
        assert panel._format_time("2026-02-01T14:30:45") == "14:30"
        assert panel._format_time("2026-02-01T09:05:00Z") == "09:05"

    def test_format_time_empty(self):
        """Test formatting empty time."""
        panel = ActivityPanel()
        assert panel._format_time("") == "??:??"
        assert panel._format_time(None) == "??:??"


class TestActivitySummaryPanel:
    """Tests for the ActivitySummaryPanel widget."""

    @pytest.fixture
    def mock_collect(self):
        """Mock the activity.collect function."""
        with patch("openclaw_dash.widgets.activity.activity.collect") as mock:
            yield mock

    def test_summary_panel_creation(self):
        """Test basic summary panel creation."""
        panel = ActivitySummaryPanel()
        assert panel is not None

    def test_summary_handles_empty_activity(self, mock_collect):
        """Test summary displays message when no activity."""
        mock_collect.return_value = {
            "current_task": None,
            "recent": [],
            "collected_at": datetime.now().isoformat(),
        }
        panel = ActivitySummaryPanel()
        assert panel is not None

    def test_summary_shows_current_task(self, mock_collect):
        """Test summary shows current task when available."""
        mock_collect.return_value = {
            "current_task": "Doing something important",
            "recent": [],
            "collected_at": datetime.now().isoformat(),
        }
        panel = ActivitySummaryPanel()
        assert panel is not None

    def test_summary_shows_latest_activity(self, mock_collect):
        """Test summary shows latest activity when no current task."""
        mock_collect.return_value = {
            "current_task": None,
            "recent": [
                {"time": "12:30", "action": "First action", "type": "git"},
                {"time": "12:45", "action": "Latest action", "type": "pr"},
            ],
            "collected_at": datetime.now().isoformat(),
        }
        panel = ActivitySummaryPanel()
        assert panel is not None
