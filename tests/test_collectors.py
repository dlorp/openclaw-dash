"""Tests for data collectors."""

from openclaw_dash.collectors import activity, channels, cron, gateway, repos, sessions


class TestGatewayCollector:
    def test_collect_returns_dict(self):
        result = gateway.collect()
        assert isinstance(result, dict)
        assert "collected_at" in result
        assert "healthy" in result

    def test_healthy_is_bool(self):
        result = gateway.collect()
        assert isinstance(result["healthy"], bool)


class TestSessionsCollector:
    def test_collect_returns_dict(self):
        result = sessions.collect()
        assert isinstance(result, dict)
        assert "sessions" in result
        assert isinstance(result["sessions"], list)

    def test_has_counts(self):
        result = sessions.collect()
        assert "total" in result
        assert "active" in result


class TestCronCollector:
    def test_collect_returns_dict(self):
        result = cron.collect()
        assert isinstance(result, dict)
        assert "jobs" in result


class TestReposCollector:
    def test_collect_returns_dict(self):
        result = repos.collect()
        assert isinstance(result, dict)
        assert "repos" in result

    def test_custom_repos_list(self):
        result = repos.collect(repos=["nonexistent-xyz-123"])
        assert result["total"] == 0


class TestActivityCollector:
    def test_collect_returns_dict(self):
        result = activity.collect()
        assert isinstance(result, dict)
        assert "current_task" in result
        assert "recent" in result


class TestChannelsCollector:
    def test_collect_returns_dict(self):
        result = channels.collect()
        assert isinstance(result, dict)
        assert "channels" in result
        assert "connected" in result
        assert "total" in result

    def test_channels_is_list(self):
        result = channels.collect()
        assert isinstance(result["channels"], list)

    def test_get_channel_icon(self):
        assert channels.get_channel_icon("discord") == "🎮"
        assert channels.get_channel_icon("telegram") == "✈️"
        assert channels.get_channel_icon("unknown") == "📱"

    def test_get_status_icon(self):
        assert channels.get_status_icon("connected") == "✓"
        assert channels.get_status_icon("disabled") == "—"
