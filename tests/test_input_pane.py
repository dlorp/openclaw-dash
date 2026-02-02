"""Tests for the input pane widget."""

from unittest.mock import MagicMock, patch

import pytest

from openclaw_dash.widgets.input_pane import (
    MAX_HISTORY,
    CommandSent,
    InputPane,
)


class TestInputPane:
    """Test InputPane widget."""

    def test_input_pane_init_defaults(self):
        """InputPane should initialize with default values."""
        pane = InputPane()
        assert pane._history == []
        assert pane._history_index == 0
        assert pane._agent is None
        assert pane._session_id is None

    def test_input_pane_init_with_agent(self):
        """InputPane should accept agent parameter."""
        pane = InputPane(agent="test-agent")
        assert pane._agent == "test-agent"
        assert pane._session_id is None

    def test_input_pane_init_with_session_id(self):
        """InputPane should accept session_id parameter."""
        pane = InputPane(session_id="test-session")
        assert pane._session_id == "test-session"
        assert pane._agent is None

    def test_set_agent(self):
        """set_agent should update the target agent."""
        pane = InputPane()
        pane.set_agent("new-agent")
        assert pane._agent == "new-agent"

    def test_set_session_id(self):
        """set_session_id should update the target session."""
        pane = InputPane()
        pane.set_session_id("new-session")
        assert pane._session_id == "new-session"

    def test_history_property(self):
        """history property should return a copy of history."""
        pane = InputPane()
        pane._history = ["cmd1", "cmd2"]
        history = pane.history
        assert history == ["cmd1", "cmd2"]
        # Should be a copy
        history.append("cmd3")
        assert pane._history == ["cmd1", "cmd2"]


class TestCommandHistory:
    """Test command history functionality."""

    def test_add_to_history(self):
        """Commands should be added to history."""
        pane = InputPane()
        pane._add_to_history("test command")
        assert "test command" in pane._history
        assert pane._history_index == 1

    def test_no_duplicate_consecutive_commands(self):
        """Consecutive duplicate commands should not be added."""
        pane = InputPane()
        pane._add_to_history("test")
        pane._add_to_history("test")
        assert len(pane._history) == 1

    def test_history_limit(self):
        """History should be limited to MAX_HISTORY entries."""
        pane = InputPane()
        for i in range(MAX_HISTORY + 10):
            pane._add_to_history(f"command {i}")
        assert len(pane._history) == MAX_HISTORY
        # Should keep most recent commands
        assert pane._history[-1] == f"command {MAX_HISTORY + 9}"

    def test_history_index_reset_after_add(self):
        """History index should reset after adding a command."""
        pane = InputPane()
        pane._add_to_history("cmd1")
        pane._history_index = 0
        pane._add_to_history("cmd2")
        assert pane._history_index == 2


class TestCommandSent:
    """Test CommandSent message."""

    def test_command_sent_success(self):
        """CommandSent should store success state."""
        msg = CommandSent("test", "response", True)
        assert msg.command == "test"
        assert msg.response == "response"
        assert msg.success is True

    def test_command_sent_failure(self):
        """CommandSent should store failure state."""
        msg = CommandSent("test", "error message", False)
        assert msg.command == "test"
        assert msg.response == "error message"
        assert msg.success is False


class TestSendCommand:
    """Test command sending functionality."""

    @patch("openclaw_dash.widgets.input_pane.subprocess.run")
    def test_send_command_success(self, mock_run):
        """Successful command should emit success message."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"content": "test response"}',
            stderr="",
        )

        pane = InputPane()
        messages = []
        pane.post_message = lambda m: messages.append(m)
        pane.add_class = MagicMock()
        pane.remove_class = MagicMock()
        pane.set_timer = MagicMock()
        pane._set_status = MagicMock()

        pane._send_command("test command")

        assert len(messages) == 1
        assert isinstance(messages[0], CommandSent)
        assert messages[0].success is True
        assert messages[0].command == "test command"

    @patch("openclaw_dash.widgets.input_pane.subprocess.run")
    def test_send_command_with_agent(self, mock_run):
        """Command with agent should include --agent flag."""
        mock_run.return_value = MagicMock(returncode=0, stdout="{}", stderr="")

        pane = InputPane(agent="test-agent")
        pane.post_message = MagicMock()
        pane.add_class = MagicMock()
        pane.remove_class = MagicMock()
        pane.set_timer = MagicMock()
        pane._set_status = MagicMock()

        pane._send_command("test")

        # Check that --agent was passed
        call_args = mock_run.call_args[0][0]
        assert "--agent" in call_args
        assert "test-agent" in call_args

    @patch("openclaw_dash.widgets.input_pane.subprocess.run")
    def test_send_command_with_session_id(self, mock_run):
        """Command with session_id should include --session-id flag."""
        mock_run.return_value = MagicMock(returncode=0, stdout="{}", stderr="")

        pane = InputPane(session_id="test-session")
        pane.post_message = MagicMock()
        pane.add_class = MagicMock()
        pane.remove_class = MagicMock()
        pane.set_timer = MagicMock()
        pane._set_status = MagicMock()

        pane._send_command("test")

        # Check that --session-id was passed
        call_args = mock_run.call_args[0][0]
        assert "--session-id" in call_args
        assert "test-session" in call_args

    @patch("openclaw_dash.widgets.input_pane.subprocess.run")
    def test_send_command_failure(self, mock_run):
        """Failed command should emit failure message."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: Something went wrong",
        )

        pane = InputPane()
        messages = []
        pane.post_message = lambda m: messages.append(m)
        pane.add_class = MagicMock()
        pane.remove_class = MagicMock()
        pane.set_timer = MagicMock()
        pane._set_status = MagicMock()

        pane._send_command("bad command")

        assert len(messages) == 1
        assert messages[0].success is False
        assert "Something went wrong" in messages[0].response

    @patch("openclaw_dash.widgets.input_pane.subprocess.run")
    def test_send_command_timeout(self, mock_run):
        """Timeout should emit failure message."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 120)

        pane = InputPane()
        messages = []
        pane.post_message = lambda m: messages.append(m)
        pane.add_class = MagicMock()
        pane.remove_class = MagicMock()
        pane.set_timer = MagicMock()
        pane._set_status = MagicMock()

        pane._send_command("slow command")

        assert len(messages) == 1
        assert messages[0].success is False
        assert "timed out" in messages[0].response.lower()

    @patch("openclaw_dash.widgets.input_pane.subprocess.run")
    def test_send_command_cli_not_found(self, mock_run):
        """Missing CLI should emit failure message."""
        mock_run.side_effect = FileNotFoundError()

        pane = InputPane()
        messages = []
        pane.post_message = lambda m: messages.append(m)
        pane.add_class = MagicMock()
        pane.remove_class = MagicMock()
        pane.set_timer = MagicMock()
        pane._set_status = MagicMock()

        pane._send_command("test")

        assert len(messages) == 1
        assert messages[0].success is False
        assert "not found" in messages[0].response.lower()


class TestInputPaneCSS:
    """Test InputPane CSS."""

    def test_has_default_css(self):
        """InputPane should have DEFAULT_CSS defined."""
        assert hasattr(InputPane, "DEFAULT_CSS")
        assert "dock: bottom" in InputPane.DEFAULT_CSS

    def test_css_contains_focus_styling(self):
        """CSS should have focus styling."""
        assert "focus-within" in InputPane.DEFAULT_CSS


class TestInputPaneBindings:
    """Test InputPane key bindings."""

    def test_has_history_bindings(self):
        """InputPane should have history navigation bindings."""
        binding_keys = [b.key for b in InputPane.BINDINGS]
        assert "up" in binding_keys
        assert "down" in binding_keys

    def test_has_escape_binding(self):
        """InputPane should have escape binding."""
        binding_keys = [b.key for b in InputPane.BINDINGS]
        assert "escape" in binding_keys


@pytest.mark.asyncio
async def test_input_pane_compose():
    """Test that InputPane composes correctly."""
    pane = InputPane()
    # Verify compose method exists
    assert hasattr(pane, "compose")
    assert callable(pane.compose)
