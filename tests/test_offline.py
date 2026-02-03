"""Tests for gateway-independent features and error handling.

Note: The gateway runs locally, so "offline mode" is a misnomer.
These tests verify the skip-gateway functionality for testing/development.
"""

from openclaw_dash.offline import (
    GATEWAY_FEATURES,
    GATEWAY_INDEPENDENT_FEATURES,
    GATEWAY_REQUIRED_FEATURES,
    OFFLINE_FEATURES,
    GatewayErrorHint,
    OfflineHint,
    disable_offline_mode,
    enable_offline_mode,
    format_gateway_error,
    format_gateway_error_short,
    get_available_offline_commands,
    get_offline_hint,
    is_offline_mode,
    should_skip_feature,
)


class TestSkipGatewayMode:
    """Tests for skip-gateway mode flag."""

    def setup_method(self):
        """Reset mode before each test."""
        disable_offline_mode()

    def test_skip_gateway_mode_default_off(self):
        """Test that skip-gateway mode is off by default."""
        assert not is_offline_mode()

    def test_enable_skip_gateway_mode(self):
        """Test enabling skip-gateway mode."""
        enable_offline_mode()
        assert is_offline_mode()

    def test_disable_skip_gateway_mode(self):
        """Test disabling skip-gateway mode."""
        enable_offline_mode()
        assert is_offline_mode()
        disable_offline_mode()
        assert not is_offline_mode()


class TestGatewayErrorHint:
    """Tests for GatewayErrorHint dataclass."""

    def test_format_message(self):
        """Test formatting hint with commands."""
        hint = GatewayErrorHint(
            feature_name="gateway",
            error_message="Gateway not responding",
            independent_commands=["cmd1", "cmd2"],
            primary_suggestion="cmd1",
        )
        msg = hint.format_message()
        assert "Gateway not responding" in msg
        assert "don't require the gateway" in msg
        assert "cmd1" in msg
        assert "cmd2" in msg

    def test_format_message_no_commands(self):
        """Test formatting hint without commands."""
        hint = GatewayErrorHint(
            feature_name="gateway",
            error_message="Gateway not responding",
            independent_commands=[],
        )
        msg = hint.format_message()
        assert "Gateway not responding" in msg
        assert "require" not in msg.lower()

    def test_format_short(self):
        """Test short format."""
        hint = GatewayErrorHint(
            feature_name="gateway",
            error_message="Gateway error",
            independent_commands=["cmd1"],
            primary_suggestion="cmd1",
        )
        short = hint.format_short()
        assert "Gateway error" in short
        assert "cmd1" in short

    def test_backwards_compat_alias(self):
        """Test that OfflineHint is an alias for GatewayErrorHint."""
        assert OfflineHint is GatewayErrorHint


class TestGetOfflineHint:
    """Tests for get_offline_hint function."""

    def test_returns_hint(self):
        """Test that get_offline_hint returns a hint."""
        hint = get_offline_hint("gateway")
        assert isinstance(hint, GatewayErrorHint)
        assert hint.feature_name == "gateway"

    def test_includes_error_message(self):
        """Test that error message is included."""
        hint = get_offline_hint("gateway", error="Connection refused")
        assert "Connection refused" in hint.error_message

    def test_has_independent_commands(self):
        """Test that independent commands are included."""
        hint = get_offline_hint("gateway")
        assert len(hint.independent_commands) > 0

    def test_timeout_gives_bug_message(self):
        """Test that timeout errors give bug-related message."""
        hint = get_offline_hint("gateway", error="Command timed out")
        assert "bug" in hint.error_message.lower()
        # Check that it suggests reporting the issue
        commands_str = " ".join(hint.independent_commands).lower()
        assert "report" in commands_str or "issue" in commands_str


class TestFormatGatewayError:
    """Tests for format_gateway_error function."""

    def test_basic_format(self):
        """Test basic error formatting."""
        msg = format_gateway_error()
        assert "Gateway" in msg
        assert "gateway start" in msg

    def test_with_error(self):
        """Test formatting with error message."""
        msg = format_gateway_error(error="Connection refused")
        assert "Connection refused" in msg

    def test_timeout_shows_bug_message(self):
        """Test that timeout errors show bug message."""
        msg = format_gateway_error(error="Command timed out")
        assert "timed out unexpectedly" in msg.lower()
        assert "bug" in msg.lower()
        assert "report" in msg.lower()

    def test_verbose_mode(self):
        """Test verbose mode includes issue reporting."""
        msg = format_gateway_error(verbose=True)
        assert "report" in msg.lower() or "issue" in msg.lower()


class TestFormatGatewayErrorShort:
    """Tests for format_gateway_error_short function."""

    def test_short_format(self):
        """Test short format is concise."""
        msg = format_gateway_error_short()
        assert "Gateway" in msg
        assert "gateway start" in msg
        assert len(msg) < 100

    def test_timeout_shows_bug_message(self):
        """Test that timeout errors show bug message."""
        msg = format_gateway_error_short(error="Command timed out")
        assert "timed out unexpectedly" in msg.lower()
        assert "bug" in msg.lower()


class TestShouldSkipFeature:
    """Tests for should_skip_feature function."""

    def setup_method(self):
        """Reset mode before each test."""
        disable_offline_mode()

    def test_returns_false_when_gateway_enabled(self):
        """Test that features are not skipped when gateway is enabled."""
        assert not should_skip_feature("sessions")

    def test_skips_gateway_features_when_disabled(self):
        """Test that gateway features are skipped when disabled."""
        enable_offline_mode()
        assert should_skip_feature("sessions")
        assert should_skip_feature("activity")
        assert should_skip_feature("gateway_status")

    def test_does_not_skip_independent_features(self):
        """Test that gateway-independent features are not skipped."""
        enable_offline_mode()
        # repos should work without gateway
        assert not should_skip_feature("repos")


class TestGetAvailableOfflineCommands:
    """Tests for get_available_offline_commands function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        commands = get_available_offline_commands()
        assert isinstance(commands, list)
        assert len(commands) > 0

    def test_command_structure(self):
        """Test that commands have proper structure."""
        commands = get_available_offline_commands()
        for cmd in commands:
            assert "command" in cmd
            assert "description" in cmd


class TestFeatureConstants:
    """Tests for feature constants."""

    def test_gateway_independent_features_defined(self):
        """Test that gateway-independent features are defined."""
        assert len(GATEWAY_INDEPENDENT_FEATURES) > 0
        assert "security" in GATEWAY_INDEPENDENT_FEATURES
        assert "auto_backup" in GATEWAY_INDEPENDENT_FEATURES

    def test_gateway_required_features_defined(self):
        """Test that gateway-required features are defined."""
        assert len(GATEWAY_REQUIRED_FEATURES) > 0
        assert "sessions" in GATEWAY_REQUIRED_FEATURES
        assert "activity" in GATEWAY_REQUIRED_FEATURES

    def test_backwards_compat_aliases(self):
        """Test that backwards-compatible aliases exist."""
        assert OFFLINE_FEATURES is GATEWAY_INDEPENDENT_FEATURES
        assert GATEWAY_FEATURES is GATEWAY_REQUIRED_FEATURES
