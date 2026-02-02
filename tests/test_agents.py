"""Tests for agents collector and widget."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from openclaw_dash.collectors import agents
from openclaw_dash.collectors.agents import Agent, AgentStatus


class TestAgentDataclass:
    """Tests for the Agent dataclass."""

    def test_running_time_seconds(self):
        """Test running time formatting for seconds."""
        agent = Agent(
            key="test",
            label="test",
            status=AgentStatus.ACTIVE,
            started_at=datetime.now() - timedelta(seconds=30),
        )
        assert "s" in agent.running_time
        assert "m" not in agent.running_time

    def test_running_time_minutes(self):
        """Test running time formatting for minutes."""
        agent = Agent(
            key="test",
            label="test",
            status=AgentStatus.ACTIVE,
            started_at=datetime.now() - timedelta(minutes=5, seconds=30),
        )
        assert "m" in agent.running_time
        assert "h" not in agent.running_time

    def test_running_time_hours(self):
        """Test running time formatting for hours."""
        agent = Agent(
            key="test",
            label="test",
            status=AgentStatus.ACTIVE,
            started_at=datetime.now() - timedelta(hours=2, minutes=15),
        )
        assert "h" in agent.running_time

    def test_to_dict(self):
        """Test Agent to_dict conversion."""
        now = datetime.now()
        agent = Agent(
            key="agent:main:subagent:test",
            label="test",
            status=AgentStatus.ACTIVE,
            started_at=now,
            task_summary="Test task",
            context_pct=25.5,
            tokens_used=50000,
        )
        result = agent.to_dict()

        assert result["key"] == "agent:main:subagent:test"
        assert result["label"] == "test"
        assert result["status"] == "active"
        assert result["task_summary"] == "Test task"
        assert result["context_pct"] == 25.5
        assert result["tokens_used"] == 50000


class TestAgentsCollector:
    """Tests for the agents collector."""

    def test_collect_returns_dict(self):
        """Test that collect returns a dict with expected keys."""
        result = agents.collect()
        assert isinstance(result, dict)
        assert "agents" in result
        assert "total" in result
        assert "active" in result
        assert "collected_at" in result

    def test_agents_is_list(self):
        """Test that agents is a list."""
        result = agents.collect()
        assert isinstance(result["agents"], list)

    def test_counts_are_integers(self):
        """Test that counts are integers."""
        result = agents.collect()
        assert isinstance(result["total"], int)
        assert isinstance(result["active"], int)

    @patch("openclaw_dash.collectors.agents.is_demo_mode")
    @patch("openclaw_dash.collectors.agents.mock_sessions")
    def test_demo_mode_returns_mock_data(self, mock_sessions, mock_demo):
        """Test that demo mode returns mock session data."""
        mock_demo.return_value = True
        mock_sessions.return_value = [
            {
                "key": "agent:main:subagent:test",
                "kind": "subagent",
                "label": "test",
                "totalTokens": 10000,
                "contextTokens": 200000,
                "updatedAt": datetime.now().timestamp() * 1000,
            }
        ]

        result = agents.collect()
        assert result["total"] == 1

    def test_get_status_icon(self):
        """Test status icons."""
        assert agents.get_status_icon("active") == "●"
        assert agents.get_status_icon("idle") == "◐"
        assert agents.get_status_icon("completed") == "✓"
        assert agents.get_status_icon("error") == "✗"
        assert agents.get_status_icon("unknown") == "?"

    def test_get_status_color(self):
        """Test status colors."""
        assert agents.get_status_color("active") == "green"
        assert agents.get_status_color("idle") == "yellow"
        assert agents.get_status_color("completed") == "dim"
        assert agents.get_status_color("error") == "red"
        assert agents.get_status_color("unknown") == "white"


class TestAgentsPanelWidget:
    """Tests for the AgentsPanel widget."""

    @pytest.fixture
    def mock_collect(self):
        """Mock the agents.collect function."""
        with patch("openclaw_dash.widgets.agents.agents.collect") as mock:
            yield mock

    def test_panel_handles_empty_agents(self, mock_collect):
        """Test panel displays message when no agents."""
        mock_collect.return_value = {
            "agents": [],
            "total": 0,
            "active": 0,
            "collected_at": datetime.now().isoformat(),
        }

        from openclaw_dash.widgets.agents import AgentsPanel

        # Create widget (won't be mounted but can test basic creation)
        panel = AgentsPanel()
        assert panel is not None

    def test_panel_handles_agents_data(self, mock_collect):
        """Test panel handles agent data correctly."""
        mock_collect.return_value = {
            "agents": [
                {
                    "key": "agent:main:subagent:test",
                    "label": "test",
                    "status": "active",
                    "running_time": "5m 30s",
                    "task_summary": "Test task",
                    "context_pct": 25.0,
                }
            ],
            "total": 1,
            "active": 1,
            "collected_at": datetime.now().isoformat(),
        }

        from openclaw_dash.widgets.agents import AgentsPanel

        panel = AgentsPanel()
        assert panel is not None


class TestAgentStatus:
    """Tests for AgentStatus enum."""

    def test_status_values(self):
        """Test that all status values are correct."""
        assert AgentStatus.ACTIVE.value == "active"
        assert AgentStatus.IDLE.value == "idle"
        assert AgentStatus.COMPLETED.value == "completed"
        assert AgentStatus.ERROR.value == "error"
