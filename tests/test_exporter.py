"""Tests for export functionality."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from openclaw_dash.exporter import (
    collect_all_data,
    export_json,
    export_markdown,
    export_to_file,
)


@pytest.fixture
def mock_collectors():
    """Mock all collectors to avoid network calls."""
    with patch("openclaw_dash.collectors.gateway.collect") as gw, \
         patch("openclaw_dash.collectors.sessions.collect") as sess, \
         patch("openclaw_dash.collectors.cron.collect") as cr, \
         patch("openclaw_dash.collectors.repos.collect") as rep, \
         patch("openclaw_dash.collectors.activity.collect") as act, \
         patch("openclaw_dash.collectors.channels.collect") as chan, \
         patch("openclaw_dash.collectors.alerts.collect") as alerts, \
         patch("openclaw_dash.metrics.CostTracker") as cost, \
         patch("openclaw_dash.metrics.PerformanceMetrics") as perf, \
         patch("openclaw_dash.metrics.GitHubMetrics") as gh:
        gw.return_value = {"healthy": True, "uptime": "1h"}
        sess.return_value = {"active": []}
        cr.return_value = {"jobs": []}
        rep.return_value = {"repos": []}
        act.return_value = {}
        chan.return_value = {"channels": []}
        alerts.return_value = {"alerts": []}
        cost.return_value.collect.return_value = {"today": {}, "summary": {}}
        perf.return_value.collect.return_value = {"summary": {}}
        gh.return_value.collect.return_value = {"streak": {}, "pr_metrics": {}}
        yield


class TestCollectAllData:
    def test_returns_dict_with_timestamp(self, mock_collectors):
        result = collect_all_data()
        assert isinstance(result, dict)
        assert "timestamp" in result
        # Verify timestamp is valid ISO format
        datetime.fromisoformat(result["timestamp"])

    def test_contains_all_sections(self, mock_collectors):
        result = collect_all_data()
        expected_keys = [
            "timestamp",
            "gateway",
            "sessions",
            "cron",
            "repos",
            "activity",
            "channels",
            "alerts",
            "metrics",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    def test_metrics_contains_subsections(self, mock_collectors):
        result = collect_all_data()
        metrics = result.get("metrics", {})
        assert "costs" in metrics
        assert "performance" in metrics
        assert "github" in metrics


class TestExportJson:
    def test_returns_valid_json(self):
        data = {"test": "value", "nested": {"key": 123}}
        result = export_json(data)
        parsed = json.loads(result)
        assert parsed == data

    def test_handles_datetime(self):
        data = {"timestamp": datetime.now()}
        result = export_json(data)
        parsed = json.loads(result)
        assert "timestamp" in parsed

    def test_pretty_prints(self):
        data = {"key": "value"}
        result = export_json(data)
        assert "\n" in result  # Should be indented


class TestExportMarkdown:
    def test_returns_string(self):
        data = {
            "timestamp": "2025-02-01T12:00:00",
            "gateway": {"healthy": True, "uptime": "1d 2h", "context_pct": 50},
            "sessions": {"active": []},
            "cron": {"jobs": []},
            "repos": {"repos": []},
            "activity": {},
            "alerts": {"alerts": []},
            "channels": {"channels": []},
            "metrics": {
                "costs": {"today": {}, "summary": {}},
                "performance": {"summary": {}},
                "github": {"streak": {}, "pr_metrics": {}},
            },
        }
        result = export_markdown(data)
        assert isinstance(result, str)
        assert "# OpenClaw Dashboard Export" in result

    def test_contains_gateway_status(self):
        data = {
            "timestamp": "2025-02-01T12:00:00",
            "gateway": {"healthy": True, "uptime": "5h", "context_pct": 25.5, "version": "1.0.0"},
            "sessions": {"active": []},
            "cron": {"jobs": []},
            "repos": {"repos": []},
            "activity": {},
            "alerts": {"alerts": []},
            "channels": {"channels": []},
            "metrics": {
                "costs": {"today": {}, "summary": {}},
                "performance": {"summary": {}},
                "github": {"streak": {}, "pr_metrics": {}},
            },
        }
        result = export_markdown(data)
        assert "## Gateway Status" in result
        assert "✅ ONLINE" in result
        assert "5h" in result

    def test_shows_offline_when_unhealthy(self):
        data = {
            "timestamp": "2025-02-01T12:00:00",
            "gateway": {"healthy": False},
            "sessions": {"active": []},
            "cron": {"jobs": []},
            "repos": {"repos": []},
            "activity": {},
            "alerts": {"alerts": []},
            "channels": {"channels": []},
            "metrics": {
                "costs": {"today": {}, "summary": {}},
                "performance": {"summary": {}},
                "github": {"streak": {}, "pr_metrics": {}},
            },
        }
        result = export_markdown(data)
        assert "❌ OFFLINE" in result

    def test_includes_sessions_table(self):
        data = {
            "timestamp": "2025-02-01T12:00:00",
            "gateway": {"healthy": True},
            "sessions": {
                "active": [
                    {"channel": "discord", "model": "claude-3", "duration": "10m"},
                    {"channel": "telegram", "model": "gpt-4", "duration": "5m"},
                ]
            },
            "cron": {"jobs": []},
            "repos": {"repos": []},
            "activity": {},
            "alerts": {"alerts": []},
            "channels": {"channels": []},
            "metrics": {
                "costs": {"today": {}, "summary": {}},
                "performance": {"summary": {}},
                "github": {"streak": {}, "pr_metrics": {}},
            },
        }
        result = export_markdown(data)
        assert "## Active Sessions" in result
        assert "discord" in result
        assert "claude-3" in result

    def test_includes_repos_table(self):
        data = {
            "timestamp": "2025-02-01T12:00:00",
            "gateway": {},
            "sessions": {"active": []},
            "cron": {"jobs": []},
            "repos": {
                "repos": [
                    {"name": "test-repo", "branch": "main", "open_prs": 2, "health": "good"}
                ]
            },
            "activity": {},
            "alerts": {"alerts": []},
            "channels": {"channels": []},
            "metrics": {
                "costs": {"today": {}, "summary": {}},
                "performance": {"summary": {}},
                "github": {"streak": {}, "pr_metrics": {}},
            },
        }
        result = export_markdown(data)
        assert "## Repositories" in result
        assert "test-repo" in result

    def test_includes_alerts_with_severity(self):
        data = {
            "timestamp": "2025-02-01T12:00:00",
            "gateway": {},
            "sessions": {"active": []},
            "cron": {"jobs": []},
            "repos": {"repos": []},
            "activity": {},
            "alerts": {
                "alerts": [
                    {"severity": "critical", "message": "Disk full"},
                    {"severity": "warning", "message": "High memory"},
                ]
            },
            "channels": {"channels": []},
            "metrics": {
                "costs": {"today": {}, "summary": {}},
                "performance": {"summary": {}},
                "github": {"streak": {}, "pr_metrics": {}},
            },
        }
        result = export_markdown(data)
        assert "## Alerts" in result
        assert "🔴" in result
        assert "Disk full" in result
        assert "🟡" in result


class TestExportToFile:
    def test_exports_json_with_explicit_path(self, mock_collectors):
        # Test with explicit output path
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath, content = export_to_file(output_path=f.name, format="json")
            assert filepath == f.name
            assert content.startswith("{")
            # Verify file was written
            written = Path(f.name).read_text()
            assert written == content
            Path(f.name).unlink()

    def test_exports_markdown_format(self, mock_collectors):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            filepath, content = export_to_file(output_path=f.name, format="md")
            assert filepath == f.name
            assert "# OpenClaw Dashboard Export" in content
            Path(f.name).unlink()

    def test_auto_generates_filename_json(self, mock_collectors, monkeypatch):
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.chdir(tmpdir)
            filepath, _ = export_to_file(format="json")
            assert filepath.startswith("openclaw-export-")
            assert filepath.endswith(".json")
            Path(filepath).unlink()

    def test_auto_generates_filename_md(self, mock_collectors, monkeypatch):
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.chdir(tmpdir)
            filepath, _ = export_to_file(format="md")
            assert filepath.startswith("openclaw-export-")
            assert filepath.endswith(".md")
            Path(filepath).unlink()


class TestCLIExport:
    @patch("sys.argv", ["openclaw-dash", "export", "--help"])
    def test_export_help(self):
        from openclaw_dash.cli import main

        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    def test_export_json_output(self, tmp_path, mock_collectors):
        from openclaw_dash.cli import main

        output_file = tmp_path / "test-export.json"
        with patch("sys.argv", ["openclaw-dash", "export", "--format", "json", "-o", str(output_file)]):
            result = main()
            assert result == 0
            assert output_file.exists()
            content = json.loads(output_file.read_text())
            assert "gateway" in content
            assert "timestamp" in content

    def test_export_markdown_output(self, tmp_path, mock_collectors):
        from openclaw_dash.cli import main

        output_file = tmp_path / "test-export.md"
        with patch("sys.argv", ["openclaw-dash", "export", "--format", "md", "-o", str(output_file)]):
            result = main()
            assert result == 0
            assert output_file.exists()
            content = output_file.read_text()
            assert "# OpenClaw Dashboard Export" in content
