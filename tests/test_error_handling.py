"""Tests for error handling and edge case coverage.

This module tests the robust error handling added to collectors and widgets,
including:
- Collector base utilities
- Widget state management
- Graceful degradation
- Error recovery
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

from openclaw_dash.collectors.base import (
    CollectorResult,
    CollectorState,
    collect_with_fallback,
    format_error_for_display,
    get_collector_state,
    get_last_success,
    is_stale,
    parse_json_output,
    run_command,
    safe_get,
    update_collector_state,
    validate_data_shape,
    with_retry,
)
from openclaw_dash.widgets.states import (
    WidgetState,
    check_and_render_state,
    format_collector_status_line,
    get_state_indicator,
    render_disconnected,
    render_empty,
    render_error,
    render_loading,
    render_stale,
    render_unavailable,
)


class TestCollectorResult:
    """Tests for CollectorResult dataclass."""

    def test_ok_result(self):
        """Test successful result properties."""
        result = CollectorResult(data={"value": 42}, state=CollectorState.OK)
        assert result.ok is True
        assert result.has_error is False
        assert result.error is None

    def test_error_result(self):
        """Test error result properties."""
        result = CollectorResult(
            data={},
            state=CollectorState.ERROR,
            error="Something went wrong",
            error_type="test_error",
        )
        assert result.ok is False
        assert result.has_error is True
        assert result.error == "Something went wrong"

    def test_timeout_result(self):
        """Test timeout result properties."""
        result = CollectorResult(
            data={},
            state=CollectorState.TIMEOUT,
            error="Command timed out",
        )
        assert result.ok is False
        assert result.has_error is True

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = CollectorResult(
            data={"key": "value"},
            state=CollectorState.OK,
            duration_ms=150.5,
        )
        d = result.to_dict()

        assert d["key"] == "value"
        assert d["_collector_state"] == "ok"
        assert d["_duration_ms"] == 150.5
        assert "_collected_at" in d

    def test_to_dict_with_error(self):
        """Test conversion includes error info."""
        result = CollectorResult(
            data={},
            state=CollectorState.ERROR,
            error="Test error",
            error_type="test_type",
            retry_count=2,
        )
        d = result.to_dict()

        assert d["_error"] == "Test error"
        assert d["_error_type"] == "test_type"
        assert d["_retry_count"] == 2


class TestCollectorStateTracking:
    """Tests for global collector state tracking."""

    def test_update_and_get_state(self):
        """Test updating and retrieving collector state."""
        result = CollectorResult(
            data={"test": True},
            state=CollectorState.OK,
        )
        update_collector_state("test_collector", result)

        retrieved = get_collector_state("test_collector")
        assert retrieved is not None
        assert retrieved.data == {"test": True}
        assert retrieved.state == CollectorState.OK

    def test_last_success_tracking(self):
        """Test last success timestamp is tracked."""
        result = CollectorResult(data={}, state=CollectorState.OK)
        update_collector_state("success_test", result)

        last = get_last_success("success_test")
        assert last is not None
        assert (datetime.now() - last).total_seconds() < 1

    def test_error_does_not_update_last_success(self):
        """Test error results don't update last success."""
        # First, register a success
        ok_result = CollectorResult(data={}, state=CollectorState.OK)
        update_collector_state("error_test", ok_result)
        first_success = get_last_success("error_test")

        # Then register an error
        error_result = CollectorResult(
            data={},
            state=CollectorState.ERROR,
            error="Test error",
        )
        update_collector_state("error_test", error_result)

        # Last success should be unchanged
        last = get_last_success("error_test")
        assert last == first_success

    def test_is_stale(self):
        """Test staleness detection."""
        # Unknown collector is stale
        assert is_stale("unknown_collector") is True

        # Recent success is not stale
        result = CollectorResult(data={}, state=CollectorState.OK)
        update_collector_state("stale_test", result)
        assert is_stale("stale_test", max_age_seconds=60) is False


class TestRunCommand:
    """Tests for run_command utility."""

    def test_successful_command(self):
        """Test successful command execution."""
        stdout, error, state = run_command(["echo", "hello"])
        assert stdout.strip() == "hello"
        assert error is None
        assert state == CollectorState.OK

    def test_command_not_found(self):
        """Test handling of missing command."""
        stdout, error, state = run_command(["nonexistent_command_xyz"])
        assert stdout is None
        assert error is not None
        assert "not found" in error.lower()
        assert state == CollectorState.UNAVAILABLE

    def test_command_timeout(self):
        """Test command timeout handling."""
        stdout, error, state = run_command(["sleep", "10"], timeout=0.1)
        assert stdout is None
        assert error is not None
        assert "timed out" in error.lower()
        assert state == CollectorState.TIMEOUT

    def test_command_failure(self):
        """Test command failure handling."""
        stdout, error, state = run_command(["false"])
        assert stdout is None
        assert error is not None
        assert state == CollectorState.ERROR


class TestParseJsonOutput:
    """Tests for parse_json_output utility."""

    def test_valid_json(self):
        """Test parsing valid JSON."""
        data, error = parse_json_output('{"key": "value"}')
        assert data == {"key": "value"}
        assert error is None

    def test_invalid_json(self):
        """Test handling of invalid JSON."""
        data, error = parse_json_output("not json")
        assert data == {}
        assert error is not None
        assert "Invalid JSON" in error

    def test_none_input(self):
        """Test handling of None input."""
        data, error = parse_json_output(None)
        assert data == {}
        assert error is not None

    def test_default_value(self):
        """Test default value on error."""
        default = {"default": True}
        data, error = parse_json_output("invalid", default=default)
        assert data == default

    def test_non_dict_json(self):
        """Test handling of non-dict JSON."""
        data, error = parse_json_output("[1, 2, 3]")
        assert data == {"data": [1, 2, 3]}
        assert error is None


class TestSafeGet:
    """Tests for safe_get utility."""

    def test_simple_key(self):
        """Test getting simple key."""
        data = {"key": "value"}
        assert safe_get(data, "key") == "value"

    def test_nested_keys(self):
        """Test getting nested keys."""
        data = {"level1": {"level2": {"level3": "deep"}}}
        assert safe_get(data, "level1", "level2", "level3") == "deep"

    def test_missing_key(self):
        """Test default on missing key."""
        data = {"key": "value"}
        assert safe_get(data, "missing") is None
        assert safe_get(data, "missing", default="default") == "default"

    def test_missing_nested(self):
        """Test default on missing nested key."""
        data = {"level1": {}}
        assert safe_get(data, "level1", "missing", "deep", default="fallback") == "fallback"

    def test_non_dict_in_path(self):
        """Test handling of non-dict in path."""
        data = {"key": "value"}
        assert safe_get(data, "key", "subkey", default="default") == "default"


class TestValidateDataShape:
    """Tests for validate_data_shape utility."""

    def test_valid_shape(self):
        """Test validation with all required keys present."""
        data = {"name": "test", "value": 42}
        is_valid, missing = validate_data_shape(data, ["name", "value"])
        assert is_valid is True
        assert missing == []

    def test_missing_keys(self):
        """Test detection of missing keys."""
        data = {"name": "test"}
        is_valid, missing = validate_data_shape(data, ["name", "value", "extra"])
        assert is_valid is False
        assert sorted(missing) == ["extra", "value"]


class TestWithRetry:
    """Tests for with_retry utility."""

    def test_success_first_try(self):
        """Test successful execution on first try."""
        call_count = 0

        def success_func():
            nonlocal call_count
            call_count += 1
            return "result"

        result, retries, error = with_retry(success_func, max_retries=3)
        assert result == "result"
        assert retries == 0
        assert error is None
        assert call_count == 1

    def test_success_after_retry(self):
        """Test success after initial failures."""
        call_count = 0

        def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"

        result, retries, error = with_retry(
            fail_then_succeed,
            max_retries=3,
            delay_seconds=0.01,
        )
        assert result == "success"
        assert retries == 2
        assert error is None

    def test_all_retries_fail(self):
        """Test exhausting all retries."""

        def always_fail():
            raise ValueError("Always fails")

        result, retries, error = with_retry(
            always_fail,
            max_retries=2,
            delay_seconds=0.01,
        )
        assert result is None
        assert retries == 2
        assert "Always fails" in error


class TestCollectWithFallback:
    """Tests for collect_with_fallback utility."""

    def test_primary_success(self):
        """Test primary collector success."""
        result = collect_with_fallback(
            primary=lambda: {"source": "primary"},
            fallback=lambda: {"source": "fallback"},
        )
        assert result == {"source": "primary"}

    def test_fallback_on_primary_failure(self):
        """Test fallback when primary fails."""

        def failing_primary():
            raise ValueError("Primary failed")

        result = collect_with_fallback(
            primary=failing_primary,
            fallback=lambda: {"source": "fallback"},
        )
        assert result == {"source": "fallback"}

    def test_default_when_both_fail(self):
        """Test default when both fail."""

        def failing():
            raise ValueError("Failed")

        result = collect_with_fallback(
            primary=failing,
            fallback=failing,
            default={"source": "default"},
        )
        assert result == {"source": "default"}

    def test_fallback_when_primary_returns_none(self):
        """Test fallback is used when primary returns None."""
        result = collect_with_fallback(
            primary=lambda: None,
            fallback=lambda: {"source": "fallback"},
        )
        assert result == {"source": "fallback"}


class TestFormatErrorForDisplay:
    """Tests for format_error_for_display utility."""

    def test_simple_error(self):
        """Test formatting simple error."""
        result = format_error_for_display("Something went wrong")
        assert result == "Something went wrong"

    def test_strips_prefix(self):
        """Test stripping common prefixes."""
        result = format_error_for_display("Error: Something went wrong")
        assert result == "Something went wrong"

    def test_truncates_long_error(self):
        """Test truncation of long errors."""
        long_error = "x" * 100
        result = format_error_for_display(long_error, max_length=50)
        assert len(result) == 50
        assert result.endswith("…")

    def test_with_error_type(self):
        """Test adding error type prefix."""
        result = format_error_for_display("Failed", error_type="network")
        assert result == "[network] Failed"

    def test_none_error(self):
        """Test handling of None error."""
        result = format_error_for_display(None)
        assert result == "Unknown error"


class TestWidgetStates:
    """Tests for widget state rendering."""

    def test_render_loading(self):
        """Test loading state rendering."""
        result = render_loading()
        assert "Loading" in result
        assert "[dim]" in result

    def test_render_loading_with_context(self):
        """Test loading with context."""
        result = render_loading("Fetching data...", context="From gateway")
        assert "Fetching data" in result
        assert "From gateway" in result

    def test_render_error(self):
        """Test error state rendering."""
        result = render_error("Connection failed", error_type="network")
        assert "Connection failed" in result
        assert "[red]" in result
        assert "network" in result

    def test_render_error_with_retry_hint(self):
        """Test error with retry hint."""
        result = render_error("Failed", retry_hint=True)
        assert "refresh" in result.lower()

    def test_render_empty(self):
        """Test empty state rendering."""
        result = render_empty("No data available")
        assert "No data" in result
        assert "[dim]" in result

    def test_render_empty_with_hint(self):
        """Test empty with hint."""
        result = render_empty("No items", hint="Create one first")
        assert "No items" in result
        assert "Create one first" in result

    def test_render_stale(self):
        """Test stale data warning."""
        # First update state
        update_collector_state(
            "stale_render_test",
            CollectorResult(data={}, state=CollectorState.OK),
        )
        result = render_stale("stale_render_test")
        assert "[yellow]" in result

    def test_render_disconnected(self):
        """Test disconnected state."""
        result = render_disconnected("gateway")
        assert "gateway" in result
        assert "[red]" in result
        assert "connect" in result.lower()

    def test_render_unavailable(self):
        """Test unavailable feature."""
        result = render_unavailable("Resources", reason="psutil not installed")
        assert "Resources" in result
        assert "unavailable" in result
        assert "psutil" in result


class TestCheckAndRenderState:
    """Tests for check_and_render_state utility."""

    def test_error_in_data(self):
        """Test detection of error in data."""
        data = {"error": "Something went wrong"}
        state, render = check_and_render_state("test", data)
        assert state == WidgetState.ERROR
        assert render is not None
        assert "Something went wrong" in render

    def test_unavailable_data(self):
        """Test detection of unavailable data."""
        # Note: available=False is checked after error, so we use a different pattern
        data = {"available": False}  # No explicit error key
        state, render = check_and_render_state("test", data)
        assert state == WidgetState.DISCONNECTED
        assert render is not None

    def test_empty_data(self):
        """Test detection of empty data."""
        data = {"items": []}
        state, render = check_and_render_state("test", data, empty_check="items")
        assert state == WidgetState.EMPTY
        assert render is None  # Widget handles empty display

    def test_loaded_data(self):
        """Test normal loaded data."""
        data = {"items": [1, 2, 3]}
        # First update state to make it not stale
        update_collector_state(
            "loaded_test",
            CollectorResult(data=data, state=CollectorState.OK),
        )
        state, render = check_and_render_state(
            "loaded_test", data, empty_check="items", max_stale_seconds=60
        )
        assert state == WidgetState.LOADED
        assert render is None


class TestGetStateIndicator:
    """Tests for get_state_indicator utility."""

    def test_no_state(self):
        """Test indicator when no state exists."""
        result = get_state_indicator("unknown_indicator_test")
        assert result == ""

    def test_ok_state(self):
        """Test indicator for OK state."""
        update_collector_state(
            "ok_indicator_test",
            CollectorResult(data={}, state=CollectorState.OK),
        )
        result = get_state_indicator("ok_indicator_test")
        assert "[green]" in result

    def test_error_state(self):
        """Test indicator for error state."""
        update_collector_state(
            "error_indicator_test",
            CollectorResult(data={}, state=CollectorState.ERROR, error="Test"),
        )
        result = get_state_indicator("error_indicator_test")
        assert "[red]" in result


class TestFormatCollectorStatusLine:
    """Tests for format_collector_status_line utility."""

    def test_unknown_collector(self):
        """Test status line for unknown collector."""
        result = format_collector_status_line("unknown_status_test")
        assert "not collected" in result

    def test_ok_collector(self):
        """Test status line for OK collector."""
        update_collector_state(
            "status_line_ok",
            CollectorResult(data={}, state=CollectorState.OK, duration_ms=42.5),
        )
        result = format_collector_status_line("status_line_ok", include_duration=True)
        assert "status_line_ok" in result
        assert "ok" in result
        assert "42" in result


class TestGatewayCollectorErrors:
    """Integration tests for gateway collector error handling."""

    @patch("openclaw_dash.collectors.gateway._try_http_health")
    @patch("openclaw_dash.collectors.gateway._try_cli_status")
    @patch("openclaw_dash.collectors.gateway.is_demo_mode")
    def test_cli_unavailable_uses_http_fallback(self, mock_demo, mock_cli, mock_http):
        """Test HTTP fallback when CLI fails."""
        mock_demo.return_value = False
        mock_cli.return_value = None
        mock_http.return_value = {"healthy": True, "mode": "test"}

        from openclaw_dash.collectors import gateway
        from openclaw_dash.collectors.cache import get_cache

        # Reset cache, circuit breaker, and connection state
        cache = get_cache()
        cache.invalidate("gateway")
        cache.reset_circuit("gateway")
        gateway._connection_failures = 0
        gateway._last_healthy = None

        result = gateway.collect()
        assert result["healthy"] is True
        mock_cli.assert_called_once()
        mock_http.assert_called_once()

    @patch("openclaw_dash.collectors.gateway._try_http_health")
    @patch("openclaw_dash.collectors.gateway._try_cli_status")
    @patch("openclaw_dash.collectors.gateway.is_demo_mode")
    def test_tracks_connection_failures(self, mock_demo, mock_cli, mock_http):
        """Test connection failure tracking."""
        mock_demo.return_value = False
        mock_cli.return_value = None
        mock_http.return_value = None  # Both methods fail

        from openclaw_dash.collectors import gateway
        from openclaw_dash.collectors.cache import get_cache

        # Reset cache, circuit breaker, and state completely
        cache = get_cache()
        cache.invalidate("gateway")
        cache.reset_circuit("gateway")
        gateway._connection_failures = 0
        gateway._last_healthy = None

        # First failure
        result1 = gateway.collect()
        assert result1["healthy"] is False
        assert result1["_consecutive_failures"] == 1

        # Invalidate cache to allow second collection
        cache.invalidate("gateway")

        # Second failure
        result2 = gateway.collect()
        assert result2["_consecutive_failures"] == 2


class TestSessionsCollectorErrors:
    """Integration tests for sessions collector error handling."""

    @patch("openclaw_dash.collectors.sessions.get_openclaw_status")
    @patch("openclaw_dash.collectors.sessions.is_demo_mode")
    def test_handles_none_status(self, mock_demo, mock_status):
        """Test handling when CLI returns None."""
        mock_demo.return_value = False
        mock_status.return_value = None

        from openclaw_dash.collectors import sessions

        result = sessions.collect()
        assert result["sessions"] == []
        assert result["_source"] == "fallback"
        assert "_reason" in result

    @patch("openclaw_dash.collectors.sessions.get_openclaw_status")
    @patch("openclaw_dash.collectors.sessions.is_demo_mode")
    def test_handles_exception(self, mock_demo, mock_status):
        """Test handling of exceptions."""
        mock_demo.return_value = False
        mock_status.side_effect = RuntimeError("Unexpected error")

        from openclaw_dash.collectors import sessions

        result = sessions.collect()
        assert result["sessions"] == []
        assert "error" in result
        assert "Unexpected error" in result["error"]


class TestCronCollectorErrors:
    """Integration tests for cron collector error handling."""

    @patch("openclaw_dash.collectors.cron.is_demo_mode")
    @patch("openclaw_dash.collectors.cron.run_command")
    def test_command_timeout(self, mock_run, mock_demo):
        """Test handling of command timeout."""
        mock_demo.return_value = False
        mock_run.return_value = (None, "Command timed out", CollectorState.TIMEOUT)

        from openclaw_dash.collectors import cron

        result = cron.collect()
        assert result["jobs"] == []
        assert "error" in result
        assert "timeout" in result["_error_type"]

    @patch("openclaw_dash.collectors.cron.is_demo_mode")
    @patch("openclaw_dash.collectors.cron.run_command")
    def test_invalid_json_response(self, mock_run, mock_demo):
        """Test handling of invalid JSON response."""
        mock_demo.return_value = False
        mock_run.return_value = ("not valid json", None, CollectorState.OK)

        from openclaw_dash.collectors import cron

        result = cron.collect()
        assert result["jobs"] == []
        assert "error" in result
        assert "json" in result["_error_type"].lower()


class TestReposCollectorErrors:
    """Integration tests for repos collector error handling."""

    @patch("openclaw_dash.collectors.repos.is_demo_mode")
    def test_missing_repos_directory(self, mock_demo):
        """Test handling when repo doesn't exist."""
        mock_demo.return_value = False

        from openclaw_dash.collectors import repos

        result = repos.collect(repos=["nonexistent-repo-xyz"])
        assert result["repos"] == []
        assert "_missing_repos" in result
        assert "nonexistent-repo-xyz" in result["_missing_repos"]

    @patch("openclaw_dash.collectors.repos.is_demo_mode")
    @patch("openclaw_dash.collectors.repos._get_open_prs")
    @patch("openclaw_dash.collectors.repos._get_last_commit")
    @patch("pathlib.Path.exists")
    def test_partial_failures_still_return_data(
        self, mock_exists, mock_commit, mock_prs, mock_demo
    ):
        """Test that partial failures still return available data."""
        mock_demo.return_value = False
        mock_exists.return_value = True
        mock_prs.return_value = (0, "gh not authenticated")
        mock_commit.return_value = ("2 hours ago", None)

        from openclaw_dash.collectors import repos

        result = repos.collect(repos=["test-repo"])

        # Should still have repo data despite PR error
        assert len(result["repos"]) == 1
        assert result["repos"][0]["name"] == "test-repo"
        assert result["repos"][0]["last_commit"] == "2 hours ago"
        assert "_errors" in result
