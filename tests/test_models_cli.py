"""Tests for the models CLI command."""

import json
from unittest.mock import patch

from openclaw_dash.services.model_discovery import ModelInfo, ModelTier


class TestModelsCLI:
    """Tests for the models CLI subcommand."""

    @patch("openclaw_dash.services.discover_local_models")
    def test_models_command_empty(self, mock_discover, capsys):
        """Test models command with no models found."""
        from openclaw_dash.cli import main

        mock_discover.return_value = []

        with patch("sys.argv", ["openclaw-dash", "models"]):
            result = main()

        assert result == 0
        captured = capsys.readouterr()
        assert "Total models: 0" in captured.out
        assert "No models found" in captured.out

    @patch("openclaw_dash.services.discover_local_models")
    def test_models_command_json_empty(self, mock_discover, capsys):
        """Test models command JSON output with no models."""
        from openclaw_dash.cli import main

        mock_discover.return_value = []

        with patch("sys.argv", ["openclaw-dash", "models", "--json"]):
            result = main()

        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["models"] == []
        assert data["total"] == 0

    @patch("openclaw_dash.services.discover_local_models")
    def test_models_command_with_models(self, mock_discover, capsys):
        """Test models command with discovered models."""
        from openclaw_dash.cli import main

        mock_discover.return_value = [
            ModelInfo(
                name="llama3.2:3b",
                provider="ollama",
                tier=ModelTier.FAST,
                family="llama",
                running=True,
            ),
            ModelInfo(
                name="qwen2:7b",
                provider="ollama",
                tier=ModelTier.FAST,
                family="qwen",
                running=False,
            ),
        ]

        with patch("sys.argv", ["openclaw-dash", "models"]):
            result = main()

        assert result == 0
        captured = capsys.readouterr()
        assert "Total models: 2" in captured.out
        assert "Running: 1" in captured.out
        assert "llama3.2:3b" in captured.out

    @patch("openclaw_dash.services.discover_local_models")
    def test_models_command_json_with_models(self, mock_discover, capsys):
        """Test models command JSON output with models."""
        from openclaw_dash.cli import main

        mock_discover.return_value = [
            ModelInfo(
                name="test-model",
                provider="ollama",
                tier=ModelTier.BALANCED,
                running=True,
            ),
        ]

        with patch("sys.argv", ["openclaw-dash", "models", "--json"]):
            result = main()

        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert len(data["models"]) == 1
        assert data["models"][0]["name"] == "test-model"
        assert data["models"][0]["tier"] == "balanced"
        assert data["running"] == 1

    @patch("openclaw_dash.services.discover_local_models")
    def test_models_command_running_filter(self, mock_discover, capsys):
        """Test models command with --running filter."""
        from openclaw_dash.cli import main

        mock_discover.return_value = []

        with patch("sys.argv", ["openclaw-dash", "models", "--running"]):
            result = main()

        assert result == 0
        # Verify discover was called with running_only=True
        mock_discover.assert_called_once_with(
            running_only=True,
            tier=None,
            provider=None,
        )

    @patch("openclaw_dash.services.discover_local_models")
    def test_models_command_tier_filter(self, mock_discover, capsys):
        """Test models command with --tier filter."""
        from openclaw_dash.cli import main

        mock_discover.return_value = []

        with patch("sys.argv", ["openclaw-dash", "models", "--tier", "fast"]):
            result = main()

        assert result == 0
        mock_discover.assert_called_once_with(
            running_only=False,
            tier="fast",
            provider=None,
        )

    @patch("openclaw_dash.services.discover_local_models")
    def test_models_command_provider_filter(self, mock_discover, capsys):
        """Test models command with --provider filter."""
        from openclaw_dash.cli import main

        mock_discover.return_value = []

        with patch("sys.argv", ["openclaw-dash", "models", "--provider", "ollama"]):
            result = main()

        assert result == 0
        mock_discover.assert_called_once_with(
            running_only=False,
            tier=None,
            provider="ollama",
        )

    @patch("openclaw_dash.services.discover_local_models")
    def test_models_command_combined_filters_json(self, mock_discover, capsys):
        """Test models command with multiple filters and JSON output."""
        from openclaw_dash.cli import main

        mock_discover.return_value = []

        with patch(
            "sys.argv",
            ["openclaw-dash", "models", "--running", "--tier", "balanced", "--json"],
        ):
            result = main()

        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["filters"]["running_only"] is True
        assert data["filters"]["tier"] == "balanced"
