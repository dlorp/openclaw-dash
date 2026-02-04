"""Tests for ASCII art utilities."""

from openclaw_dash.widgets.ascii_art import (
    BRAND_COLORS,
    DOUBLE,
    ROUNDED,
    SINGLE,
    STATUS_SYMBOLS,
    draw_box,
    format_with_trend,
    get_border_chars,
    mini_bar,
    progress_bar,
    separator,
    sparkline,
    status_indicator,
    trend_indicator,
)


class TestBorderChars:
    """Test border character retrieval."""

    def test_single_border(self):
        chars = get_border_chars("single")
        assert chars == SINGLE
        assert chars["tl"] == "┌"
        assert chars["br"] == "┘"

    def test_double_border(self):
        chars = get_border_chars("double")
        assert chars == DOUBLE
        assert chars["tl"] == "╔"
        assert chars["br"] == "╝"

    def test_rounded_border(self):
        chars = get_border_chars("rounded")
        assert chars == ROUNDED
        assert chars["tl"] == "╭"
        assert chars["br"] == "╯"


class TestDrawBox:
    """Test box drawing functionality."""

    def test_simple_box(self):
        result = draw_box("Hello", style="single")
        lines = result.split("\n")
        assert len(lines) == 3
        assert lines[0].startswith("┌")
        assert lines[0].endswith("┐")
        assert lines[2].startswith("└")
        assert lines[2].endswith("┘")
        assert "Hello" in lines[1]

    def test_box_with_title(self):
        result = draw_box("Content", title="Title", style="single")
        assert "Title" in result.split("\n")[0]

    def test_multiline_content(self):
        result = draw_box(["Line 1", "Line 2", "Line 3"])
        lines = result.split("\n")
        assert len(lines) == 5  # top + 3 content + bottom

    def test_double_border_style(self):
        result = draw_box("Test", style="double")
        assert "╔" in result
        assert "╝" in result

    def test_rounded_border_style(self):
        result = draw_box("Test", style="rounded")
        assert "╭" in result
        assert "╯" in result


class TestSparkline:
    """Test sparkline generation."""

    def test_empty_values(self):
        assert sparkline([]) == ""

    def test_single_value(self):
        result = sparkline([5])
        assert len(result) == 1
        assert result in "▁▂▃▄▅▆▇█"

    def test_ascending_values(self):
        result = sparkline([1, 2, 3, 4, 5, 6, 7, 8])
        assert len(result) == 8
        # First should be lowest, last should be highest
        assert result[0] == "▁"
        assert result[-1] == "█"

    def test_all_same_values(self):
        result = sparkline([5, 5, 5, 5])
        # Should all be the same middle-ish character
        assert len(set(result)) == 1

    def test_width_limit(self):
        result = sparkline([1, 2, 3, 4, 5], width=3)
        assert len(result) == 3
        # Should use last 3 values
        assert result[-1] == "█"

    def test_custom_min_max(self):
        result = sparkline([5], min_val=0, max_val=10)
        # Value 5 is 50% of range, should be middle character
        assert result in "▄▅"


class TestProgressBar:
    """Test progress bar generation."""

    def test_zero_progress(self):
        result = progress_bar(0.0, width=10, show_percent=False)
        assert "█" not in result
        assert "░" in result

    def test_full_progress(self):
        result = progress_bar(1.0, width=10, show_percent=False)
        assert "░" not in result
        assert "█" in result

    def test_half_progress(self):
        result = progress_bar(0.5, width=10, show_percent=False)
        assert "█" in result
        assert "░" in result

    def test_with_percent(self):
        result = progress_bar(0.5, width=10, show_percent=True)
        assert "50" in result
        assert "%" in result

    def test_ascii_style(self):
        result = progress_bar(0.5, width=10, style="ascii", show_percent=False)
        assert "[" in result
        assert "]" in result
        assert "=" in result
        assert "-" in result

    def test_clamps_values(self):
        result_low = progress_bar(-0.5, width=10, show_percent=False)
        result_high = progress_bar(1.5, width=10, show_percent=False)
        assert "░" in result_low  # Should be 0%
        assert "░" not in result_high  # Should be 100%


class TestStatusIndicator:
    """Test status indicator generation."""

    def test_ok_status(self):
        result = status_indicator("ok")
        assert STATUS_SYMBOLS["ok"] in result
        assert "#50D8D7" in result  # Medium Turquoise brand color

    def test_error_status(self):
        result = status_indicator("error")
        assert STATUS_SYMBOLS["error"] in result
        assert "#FF5252" in result  # Error red

    def test_warning_status(self):
        result = status_indicator("warning")
        assert STATUS_SYMBOLS["warning"] in result
        assert "#FB8B24" in result  # Dark Orange brand color

    def test_with_label(self):
        result = status_indicator("ok", label="Success")
        assert "Success" in result

    def test_no_color(self):
        result = status_indicator("ok", color=False)
        assert "[" not in result
        assert STATUS_SYMBOLS["ok"] in result

    def test_unknown_status(self):
        result = status_indicator("unknown_status")
        assert STATUS_SYMBOLS["bullet"] in result


class TestSeparator:
    """Test separator generation."""

    def test_thin_separator(self):
        result = separator(10, style="thin")
        assert result == "─" * 10

    def test_double_separator(self):
        result = separator(10, style="double")
        assert result == "═" * 10

    def test_with_label(self):
        result = separator(20, label="Test")
        assert "Test" in result
        assert len(result) == 20

    def test_dotted_style(self):
        result = separator(10, style="dotted")
        assert "┄" in result


class TestMiniBar:
    """Test mini bar generation."""

    def test_zero_value(self):
        result = mini_bar(0.0, width=5)
        assert len(result) == 5
        assert "█" not in result

    def test_full_value(self):
        result = mini_bar(1.0, width=5)
        assert "█" in result

    def test_partial_value(self):
        result = mini_bar(0.5, width=8)
        assert len(result) == 8

    def test_clamps_values(self):
        result_low = mini_bar(-0.5, width=5)
        result_high = mini_bar(1.5, width=5)
        assert len(result_low) == 5
        assert len(result_high) == 5


class TestTrendIndicator:
    """Test trend indicator generation."""

    def test_upward_trend(self):
        result = trend_indicator(110, 100)
        assert STATUS_SYMBOLS["arrow_up"] in result
        assert "green" in result

    def test_downward_trend(self):
        result = trend_indicator(90, 100)
        assert STATUS_SYMBOLS["arrow_down"] in result
        assert "red" in result

    def test_stable_trend(self):
        result = trend_indicator(101, 100)  # 1% change, below threshold
        assert STATUS_SYMBOLS["bullet"] in result

    def test_zero_previous(self):
        result = trend_indicator(100, 0)
        assert STATUS_SYMBOLS["bullet"] in result


class TestFormatWithTrend:
    """Test format with trend helper."""

    def test_basic_format(self):
        result = format_with_trend("CPU", "50%")
        assert "[bold]CPU:[/]" in result
        assert "50%" in result

    def test_with_sparkline(self):
        result = format_with_trend("CPU", "50%", trend_values=[10, 20, 30, 40, 50])
        assert "CPU" in result
        assert "50%" in result
        # Should contain sparkline characters
        assert any(c in result for c in "▁▂▃▄▅▆▇█")

    def test_with_single_value_no_sparkline(self):
        result = format_with_trend("CPU", "50%", trend_values=[50])
        # Single value shouldn't add sparkline
        assert "▁" not in result or "█" not in result


class TestStatusSymbols:
    """Test that all expected status symbols are present."""

    def test_common_symbols_exist(self):
        assert "ok" in STATUS_SYMBOLS
        assert "error" in STATUS_SYMBOLS
        assert "warning" in STATUS_SYMBOLS
        assert "running" in STATUS_SYMBOLS
        assert "stopped" in STATUS_SYMBOLS

    def test_arrow_symbols(self):
        assert "arrow_up" in STATUS_SYMBOLS
        assert "arrow_down" in STATUS_SYMBOLS
        assert "arrow_left" in STATUS_SYMBOLS
        assert "arrow_right" in STATUS_SYMBOLS

    def test_shape_symbols(self):
        assert "circle_full" in STATUS_SYMBOLS
        assert "circle_empty" in STATUS_SYMBOLS
        assert "square_full" in STATUS_SYMBOLS
        assert "square_empty" in STATUS_SYMBOLS


class TestBrandColors:
    """Test brand colors are properly defined for widget use."""

    def test_brand_colors_dict_exists(self):
        """BRAND_COLORS dictionary should exist."""
        assert isinstance(BRAND_COLORS, dict)

    def test_all_brand_colors_present(self):
        """All dlorp brand colors should be present."""
        expected_keys = [
            "granite_gray",
            "dark_orange",
            "titanium_yellow",
            "medium_turquoise",
            "royal_blue",
        ]
        for key in expected_keys:
            assert key in BRAND_COLORS, f"Missing brand color: {key}"

    def test_brand_colors_are_valid_hex(self):
        """All brand colors should be valid hex codes."""
        for name, color in BRAND_COLORS.items():
            assert color.startswith("#"), f"{name} should start with #"
            assert len(color) == 7, f"{name} should be 7 chars (e.g., #RRGGBB)"
            # Validate hex
            try:
                int(color[1:], 16)
            except ValueError:
                raise AssertionError(f"{name} ({color}) is not valid hex")

    def test_granite_gray_for_borders(self):
        """Granite Gray should be #636764 for borders."""
        assert BRAND_COLORS["granite_gray"] == "#636764"

    def test_dark_orange_for_warnings(self):
        """Dark Orange should be #FB8B24 for warnings."""
        assert BRAND_COLORS["dark_orange"] == "#FB8B24"

    def test_medium_turquoise_for_success(self):
        """Medium Turquoise should be #50D8D7 for success."""
        assert BRAND_COLORS["medium_turquoise"] == "#50D8D7"
