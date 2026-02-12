"""Tests for metrics collectors."""

import json
from unittest.mock import patch

from openclaw_dash import demo
from openclaw_dash.metrics import MAX_TOKENS, CostTracker, _validate_token_count


class TestCostTracker:
    """Tests for CostTracker."""

    def test_collect_returns_dict(self, tmp_path):
        tracker = CostTracker(metrics_dir=tmp_path)
        result = tracker.collect()
        assert isinstance(result, dict)
        assert "today" in result
        assert "summary" in result
        assert "trend" in result
        assert "collected_at" in result

    def test_today_structure(self, tmp_path):
        tracker = CostTracker(metrics_dir=tmp_path)
        result = tracker.collect()
        today = result["today"]
        assert "date" in today
        assert "input_tokens" in today
        assert "output_tokens" in today
        assert "cost" in today

    def test_calculate_cost_opus(self):
        # Test opus pricing: $15/1M input, $75/1M output
        input_cost, output_cost, total = CostTracker.calculate_cost(
            "claude-opus-4-5",
            input_tokens=1_000_000,
            output_tokens=100_000,
        )
        assert input_cost == 15.00
        assert output_cost == 7.50
        assert total == 22.50

    def test_calculate_cost_sonnet(self):
        # Test sonnet pricing: $3/1M input, $15/1M output
        input_cost, output_cost, total = CostTracker.calculate_cost(
            "claude-sonnet-4",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        assert input_cost == 3.00
        assert output_cost == 15.00
        assert total == 18.00

    def test_calculate_cost_unknown_model(self):
        # Unknown models should use sonnet pricing as fallback
        input_cost, output_cost, total = CostTracker.calculate_cost(
            "unknown-model",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        assert total > 0  # Should get some value, not crash

    def test_history_persistence(self, tmp_path):
        demo.disable_demo_mode()  # Disable demo mode to test real code path
        tracker = CostTracker(metrics_dir=tmp_path)

        # First collection creates daily entry even if no sessions
        tracker.collect()

        # History is saved internally, verify by loading
        history = tracker._load_history()
        assert "daily" in history
        assert "sessions" in history

        # Today's date should be in daily
        from datetime import date

        today = date.today().isoformat()
        assert today in history["daily"]

    def test_get_history(self, tmp_path):
        tracker = CostTracker(metrics_dir=tmp_path)
        tracker.collect()

        history = tracker.get_history(days=30)
        assert isinstance(history, list)

    def test_sessions_data_from_collector(self, tmp_path):
        with patch("openclaw_dash.collectors.sessions.collect") as mock_collect:
            mock_collect.return_value = {
                "sessions": [
                    {
                        "key": "test-session",
                        "model": "claude-sonnet-4",
                        "inputTokens": 1000,
                        "outputTokens": 500,
                        "totalTokens": 1500,
                    }
                ]
            }

            tracker = CostTracker(metrics_dir=tmp_path)
            sessions = tracker.get_sessions_data()
            assert isinstance(sessions, list)
            assert len(sessions) == 1
            assert sessions[0]["key"] == "test-session"


class TestSecurityValidation:
    """Security-focused tests for token validation and DoS protection."""

    def test_validate_token_count_valid_int(self):
        """Valid integer should pass through unchanged."""
        assert _validate_token_count(1000, "test") == 1000
        assert _validate_token_count(0, "test") == 0
        assert _validate_token_count(MAX_TOKENS, "test") == MAX_TOKENS

    def test_validate_token_count_string_coercion(self):
        """Valid numeric strings should be coerced to int."""
        assert _validate_token_count("1000", "test") == 1000
        assert _validate_token_count("0", "test") == 0

    def test_validate_token_count_invalid_type(self):
        """Invalid types should return 0 and log warning."""
        assert _validate_token_count("not-a-number", "test") == 0
        assert _validate_token_count(None, "test") == 0
        assert _validate_token_count([], "test") == 0
        assert _validate_token_count({}, "test") == 0
        assert _validate_token_count(3.14159, "test") == 3  # Float should truncate

    def test_validate_token_count_negative(self):
        """Negative values should be clamped to 0."""
        assert _validate_token_count(-1, "test") == 0
        assert _validate_token_count(-1000, "test") == 0

    def test_validate_token_count_overflow(self):
        """Values exceeding MAX_TOKENS should be clamped."""
        assert _validate_token_count(MAX_TOKENS + 1, "test") == MAX_TOKENS
        assert _validate_token_count(999_999_999, "test") == MAX_TOKENS

    def test_collect_with_malformed_token_data(self, tmp_path):
        """Collector should handle malformed token data gracefully."""
        with patch("openclaw_dash.collectors.sessions.collect") as mock_collect:
            mock_collect.return_value = {
                "sessions": [
                    {
                        "key": "session-1",
                        "model": "claude-sonnet-4",
                        "inputTokens": "not-a-number",  # Type confusion
                        "outputTokens": -500,  # Negative value
                        "totalTokens": 999_999_999,  # Overflow
                    },
                    {
                        "key": "session-2",
                        "model": "claude-sonnet-4",
                        "inputTokens": None,  # None type
                        "outputTokens": [],  # Invalid type
                        "totalTokens": "1500",  # String but valid
                    },
                ]
            }

            tracker = CostTracker(metrics_dir=tmp_path)
            result = tracker.collect()

            # Should not crash and should return valid structure
            assert isinstance(result, dict)
            assert "today" in result
            assert isinstance(result["today"]["input_tokens"], int)
            assert isinstance(result["today"]["output_tokens"], int)

    def test_load_history_file_size_limit(self, tmp_path):
        """Should reject files exceeding size limit."""
        tracker = CostTracker(metrics_dir=tmp_path)

        # Create a file larger than MAX_COSTS_FILE_SIZE
        large_data = {"daily": {}, "sessions": {}, "padding": "x" * (11 * 1024 * 1024)}
        tracker.costs_file.write_text(json.dumps(large_data))

        history = tracker._load_history()

        # Should return empty default structure
        assert history == {"daily": {}, "sessions": {}}

    def test_load_history_deeply_nested_json(self, tmp_path):
        """Should handle deeply nested JSON without crashing."""
        tracker = CostTracker(metrics_dir=tmp_path)

        # Create a deeply nested JSON string directly to avoid RecursionError during encoding
        # This tests that _load_history() can handle RecursionError during parsing
        depth = 1000
        deeply_nested_json = '{"nested":' * depth + "{}" + "}" * depth

        tracker.costs_file.write_text(deeply_nested_json)

        # Should not crash and should return default structure
        history = tracker._load_history()
        assert isinstance(history, dict)

    def test_load_history_invalid_json(self, tmp_path):
        """Should handle invalid JSON gracefully."""
        tracker = CostTracker(metrics_dir=tmp_path)

        # Write invalid JSON
        tracker.costs_file.write_text("{invalid json content")

        history = tracker._load_history()

        # Should return empty default structure
        assert history == {"daily": {}, "sessions": {}}

    def test_load_history_file_not_exists(self, tmp_path):
        """Should handle missing file gracefully."""
        tracker = CostTracker(metrics_dir=tmp_path)

        # Ensure file doesn't exist
        if tracker.costs_file.exists():
            tracker.costs_file.unlink()

        history = tracker._load_history()

        # Should return empty default structure
        assert history == {"daily": {}, "sessions": {}}
