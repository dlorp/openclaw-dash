"""Tests for CLI."""

import pytest
from unittest.mock import patch
from openclaw_dash.cli import main, get_status


class TestCLI:
    def test_get_status_returns_dict(self):
        result = get_status()
        assert isinstance(result, dict)
        assert "gateway" in result
        assert "sessions" in result
        assert "repos" in result
        assert "activity" in result

    @patch("sys.argv", ["openclaw-dash", "--version"])
    def test_version_flag(self):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    @patch("sys.argv", ["openclaw-dash", "--status", "--json"])
    def test_json_output(self, capsys):
        result = main()
        assert result == 0
        import json
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "gateway" in data
