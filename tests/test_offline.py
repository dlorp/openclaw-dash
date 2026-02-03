"""Tests for offline mode utilities."""

from openclaw_dash.offline import (
    GATEWAY_FEATURES,
    OFFLINE_FEATURES,
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


class TestOfflineMode:
    """Tests for offline mode flag."""

    def setup_method(self):
        """Reset offline mode before each test."""
        disable_offline_mode()

    def test_offline_mode_default_off(self):
        """Test that offline mode is off by default."""
        assert not is_offline_mode()

    def test_enable_offline_mode(self):
        """Test enabling offline mode."""
        enable_offline_mode()
        assert is_offline_mode()

    def test_disable_offline_mode(self):
        """Test disabling offline mode."""
        enable_offline_mode()
        assert is_offline_mode()
        disable_offline_mode()
        assert not is_offline_mode()


class TestOfflineHint:
    """Tests for OfflineHint dataclass."""

    def test_format_message(self):
        """Test formatting hint with alternatives."""
        hint = OfflineHint(
            feature_name="gateway",
            error_message="Gateway not available",
            offline_alternatives=["cmd1", "cmd2"],
            primary_alternative="cmd1",
        )
        msg = hint.format_message()
        assert "Gateway not available" in msg
        assert "Offline alternatives:" in msg
        assert "cmd1" in msg
        assert "cmd2" in msg

    def test_format_message_no_alternatives(self):
        """Test formatting hint without alternatives."""
        hint = OfflineHint(
            feature_name="gateway",
            error_message="Gateway not available",
            offline_alternatives=[],
        )
        msg = hint.format_message()
        assert "Gateway not available" in msg
        assert "alternatives" not in msg.lower()

    def test_format_short(self):
        """Test short format."""
        hint = OfflineHint(
            feature_name="gateway",
            error_message="Gateway offline",
            offline_alternatives=["cmd1"],
            primary_alternative="cmd1",
        )
        short = hint.format_short()
        assert "Gateway offline" in short
        assert "cmd1" in short


class TestGetOfflineHint:
    """Tests for get_offline_hint function."""

    def test_returns_hint(self):
        """Test that get_offline_hint returns a hint."""
        hint = get_offline_hint("gateway")
        assert isinstance(hint, OfflineHint)
        assert hint.feature_name == "gateway"

    def test_includes_error_message(self):
        """Test that error message is included."""
        hint = get_offline_hint("gateway", error="Connection refused")
        assert "Connection refused" in hint.error_message

    def test_has_alternatives(self):
        """Test that alternatives are included."""
        hint = get_offline_hint("gateway")
        assert len(hint.offline_alternatives) > 0


class TestFormatGatewayError:
    """Tests for format_gateway_error function."""

    def test_basic_format(self):
        """Test basic error formatting."""
        msg = format_gateway_error()
        assert "Gateway not available" in msg
        assert "offline" in msg.lower()

    def test_with_error(self):
        """Test formatting with error message."""
        msg = format_gateway_error(error="Connection refused")
        assert "Connection refused" in msg

    def test_includes_alternatives(self):
        """Test that alternatives are included."""
        msg = format_gateway_error()
        assert "security" in msg
        assert "backup" in msg

    def test_verbose_mode(self):
        """Test verbose mode includes more info."""
        msg = format_gateway_error(verbose=True)
        assert "pr-tracker" in msg.lower()


class TestFormatGatewayErrorShort:
    """Tests for format_gateway_error_short function."""

    def test_short_format(self):
        """Test short format is concise."""
        msg = format_gateway_error_short()
        assert "Gateway offline" in msg
        assert "security" in msg
        assert len(msg) < 100


class TestShouldSkipFeature:
    """Tests for should_skip_feature function."""

    def setup_method(self):
        """Reset offline mode before each test."""
        disable_offline_mode()

    def test_returns_false_when_not_offline(self):
        """Test that features are not skipped when online."""
        assert not should_skip_feature("sessions")

    def test_skips_gateway_features_when_offline(self):
        """Test that gateway features are skipped when offline."""
        enable_offline_mode()
        assert should_skip_feature("sessions")
        assert should_skip_feature("activity")
        assert should_skip_feature("gateway_status")

    def test_does_not_skip_offline_features(self):
        """Test that offline features are not skipped."""
        enable_offline_mode()
        # repos should work offline
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


class TestOfflineFeatures:
    """Tests for offline/gateway feature constants."""

    def test_offline_features_defined(self):
        """Test that offline features are defined."""
        assert len(OFFLINE_FEATURES) > 0
        assert "security" in OFFLINE_FEATURES
        assert "auto_backup" in OFFLINE_FEATURES

    def test_gateway_features_defined(self):
        """Test that gateway features are defined."""
        assert len(GATEWAY_FEATURES) > 0
        assert "sessions" in GATEWAY_FEATURES
        assert "activity" in GATEWAY_FEATURES
