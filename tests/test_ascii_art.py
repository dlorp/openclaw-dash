"""Tests for ASCII art styling utilities."""

from openclaw_dash.widgets.ascii_art import (
    DOUBLE_BOX,
    SINGLE_BOX,
    draw_box,
    progress_bar,
    sparkline,
    status_icon,
)


class TestDrawBox:
    """Tests for draw_box function."""

    def test_empty_content(self):
        """Box with no content."""
        result = draw_box([])
        assert len(result) == 2  # top + bottom borders
        assert result[0].startswith(SINGLE_BOX["tl"])
        assert result[1].startswith(SINGLE_BOX["bl"])

    def test_single_line(self):
        """Box with single line of content."""
        result = draw_box(["hello"])
        assert len(result) == 3
        assert "hello" in result[1]
        assert result[1].startswith(SINGLE_BOX["v"])
        assert result[1].endswith(SINGLE_BOX["v"])

    def test_multiple_lines(self):
        """Box with multiple lines pads correctly."""
        result = draw_box(["short", "longer line"])
        assert len(result) == 4
        # Both content lines should be same width
        assert len(result[1]) == len(result[2])

    def test_double_border(self):
        """Double-line border style."""
        result = draw_box(["test"], double=True)
        assert result[0].startswith(DOUBLE_BOX["tl"])
        assert result[1].startswith(DOUBLE_BOX["v"])
        assert result[2].startswith(DOUBLE_BOX["bl"])

    def test_title(self):
        """Box with title in top border."""
        result = draw_box(["content"], title="Title")
        assert "Title" in result[0]

    def test_min_width(self):
        """Box respects minimum width."""
        result = draw_box(["hi"], min_width=20)
        # Border adds 4 chars (corners + spaces)
        assert len(result[0]) >= 24


class TestSparkline:
    """Tests for sparkline function."""

    def test_empty_values(self):
        """Empty input returns empty string."""
        assert sparkline([]) == ""

    def test_constant_values(self):
        """Constant values produce consistent blocks."""
        result = sparkline([5, 5, 5, 5])
        assert len(result) == 4
        # All blocks should be the same
        assert len(set(result)) == 1

    def test_ascending_values(self):
        """Ascending values produce ascending blocks."""
        result = sparkline([0, 1, 2, 3])
        assert len(result) == 4
        # First should be lowest block, last highest
        assert result[0] == " "
        assert result[-1] == "█"

    def test_width_resampling(self):
        """Sparkline resamples to specified width."""
        result = sparkline([1, 2, 3, 4, 5, 6, 7, 8], width=4)
        assert len(result) == 4

    def test_negative_values(self):
        """Handles negative values correctly."""
        result = sparkline([-10, 0, 10])
        assert len(result) == 3
        assert result[0] == " "  # lowest
        assert result[-1] == "█"  # highest


class TestProgressBar:
    """Tests for progress_bar function."""

    def test_zero_progress(self):
        """Zero progress shows empty bar."""
        result = progress_bar(0.0, width=10, show_percent=False)
        assert result == "░" * 10

    def test_full_progress(self):
        """Full progress shows filled bar."""
        result = progress_bar(1.0, width=10, show_percent=False)
        assert result == "█" * 10

    def test_half_progress(self):
        """Half progress shows half filled."""
        result = progress_bar(0.5, width=10, show_percent=False)
        assert result == "█" * 5 + "░" * 5

    def test_with_percent(self):
        """Progress bar includes percentage."""
        result = progress_bar(0.75, width=10)
        assert "75.0%" in result

    def test_clamps_values(self):
        """Values outside 0-1 are clamped."""
        assert progress_bar(-0.5, width=10, show_percent=False) == "░" * 10
        assert progress_bar(1.5, width=10, show_percent=False) == "█" * 10

    def test_custom_characters(self):
        """Custom fill characters work."""
        result = progress_bar(0.5, width=4, show_percent=False, filled="#", empty="-")
        assert result == "##--"


class TestStatusIcon:
    """Tests for status_icon function."""

    def test_known_statuses(self):
        """Known status keys return expected symbols."""
        assert status_icon("ok") == "●"
        assert status_icon("warn") == "◐"
        assert status_icon("error") == "○"
        assert status_icon("up") == "▲"
        assert status_icon("down") == "▼"

    def test_case_insensitive(self):
        """Status lookup is case insensitive."""
        assert status_icon("OK") == status_icon("ok")
        assert status_icon("Error") == status_icon("error")

    def test_unknown_status(self):
        """Unknown status returns unknown symbol."""
        assert status_icon("invalid") == "◌"
        assert status_icon("") == "◌"
