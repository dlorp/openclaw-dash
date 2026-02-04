"""Tests for the SessionsPanel widget (token-based highlighting)."""

from openclaw_dash.widgets.sessions_panel import (
    CRITICAL_TOKEN_THRESHOLD,
    WARN_TOKEN_THRESHOLD,
    format_tokens,
    get_token_color,
    get_token_glyph,
    parse_channel_from_key,
)


class TestFormatTokens:
    """Tests for token formatting."""

    def test_small_tokens(self):
        """Should return raw number for small values."""
        assert format_tokens(500) == "500"
        assert format_tokens(0) == "0"

    def test_thousands(self):
        """Should format thousands with k suffix."""
        assert format_tokens(1000) == "1k"
        assert format_tokens(45_000) == "45k"
        assert format_tokens(999_999) == "999k"

    def test_millions(self):
        """Should format millions with M suffix."""
        assert format_tokens(1_000_000) == "1.0M"
        assert format_tokens(2_500_000) == "2.5M"


class TestGetTokenColor:
    """Tests for token color coding."""

    def test_low_tokens_green(self):
        """Should return green for low token counts."""
        assert get_token_color(0) == "green"
        assert get_token_color(10_000) == "green"
        assert get_token_color(49_999) == "green"

    def test_warn_tokens_yellow(self):
        """Should return yellow for warning threshold."""
        assert get_token_color(WARN_TOKEN_THRESHOLD) == "yellow"
        assert get_token_color(75_000) == "yellow"
        assert get_token_color(99_999) == "yellow"

    def test_critical_tokens_red(self):
        """Should return red for critical threshold."""
        assert get_token_color(CRITICAL_TOKEN_THRESHOLD) == "red"
        assert get_token_color(150_000) == "red"


class TestGetTokenGlyph:
    """Tests for token status glyphs."""

    def test_low_tokens_bullet(self):
        """Should return bullet for low tokens."""
        assert get_token_glyph(0) == "●"
        assert get_token_glyph(49_999) == "●"

    def test_warn_tokens_triangle(self):
        """Should return warning triangle for medium tokens."""
        assert get_token_glyph(WARN_TOKEN_THRESHOLD) == "▲"
        assert get_token_glyph(75_000) == "▲"

    def test_critical_tokens_diamond(self):
        """Should return diamond for critical tokens."""
        assert get_token_glyph(CRITICAL_TOKEN_THRESHOLD) == "◆"
        assert get_token_glyph(200_000) == "◆"


class TestParseChannelFromKey:
    """Tests for channel parsing from session keys."""

    def test_discord_channel(self):
        """Should extract discord from key."""
        key = "agent:main:discord:channel:1234567890"
        assert parse_channel_from_key(key) == "discord"

    def test_telegram_channel(self):
        """Should extract telegram from key."""
        key = "agent:florp:telegram:chat:9876"
        assert parse_channel_from_key(key) == "telegram"

    def test_local_main(self):
        """Should return local for main sessions."""
        key = "agent:main:main"
        assert parse_channel_from_key(key) == "local"

    def test_local_subagent(self):
        """Should return local for subagent sessions."""
        key = "agent:florp:subagent:abc123"
        assert parse_channel_from_key(key) == "local"

    def test_empty_key(self):
        """Should return dash for empty key."""
        assert parse_channel_from_key("") == "-"
        assert parse_channel_from_key(None) == "-"

    def test_unknown_format(self):
        """Should return dash for unrecognized format."""
        key = "some:random:key"
        assert parse_channel_from_key(key) == "-"


class TestThresholds:
    """Tests for threshold constants."""

    def test_warn_threshold(self):
        """Warn threshold should be 50k."""
        assert WARN_TOKEN_THRESHOLD == 50_000

    def test_critical_threshold(self):
        """Critical threshold should be 100k."""
        assert CRITICAL_TOKEN_THRESHOLD == 100_000
