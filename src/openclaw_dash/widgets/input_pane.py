"""Input pane widget for sending commands to OpenClaw."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Input, Static

if TYPE_CHECKING:
    pass

# Maximum command history size
MAX_HISTORY = 100


class CommandSent(Message):
    """Message emitted when a command is sent."""

    def __init__(self, command: str, response: str, success: bool) -> None:
        self.command = command
        self.response = response
        self.success = success
        super().__init__()


class InputPane(Static):
    """Input pane for sending commands/messages to OpenClaw.

    Features:
    - Text input with command history (up/down arrows)
    - Send to OpenClaw agent API
    - Visual feedback for command status
    """

    DEFAULT_CSS = """
    InputPane {
        dock: bottom;
        height: auto;
        min-height: 3;
        max-height: 5;
        background: $surface;
        border-top: solid $primary;
        padding: 0 1;
    }

    InputPane:focus-within {
        border-top: solid $warning;
    }

    InputPane #input-container {
        height: auto;
        width: 100%;
        padding: 0;
    }

    InputPane #command-input {
        width: 1fr;
        border: none;
        background: $surface;
        padding: 0 1;
    }

    InputPane #command-input:focus {
        border: none;
    }

    InputPane #input-prompt {
        width: auto;
        padding: 0;
        color: $primary;
        text-style: bold;
    }

    InputPane #input-status {
        width: auto;
        padding: 0 1;
        color: $text-muted;
    }

    InputPane.sending #input-status {
        color: $warning;
    }

    InputPane.error #input-status {
        color: $error;
    }

    InputPane.success #input-status {
        color: $success;
    }
    """

    BINDINGS = [
        Binding("up", "history_prev", "Previous command", show=False),
        Binding("down", "history_next", "Next command", show=False),
        Binding("escape", "blur_input", "Unfocus", show=False),
    ]

    def __init__(
        self,
        agent: str | None = None,
        session_id: str | None = None,
        **kwargs,
    ) -> None:
        """Initialize the input pane.

        Args:
            agent: Default agent to send commands to.
            session_id: Default session ID to use.
            **kwargs: Additional arguments for Static.
        """
        super().__init__(**kwargs)
        self._history: list[str] = []
        self._history_index: int = 0
        self._current_input: str = ""
        self._agent = agent
        self._session_id = session_id

    def compose(self) -> ComposeResult:
        with Horizontal(id="input-container"):
            yield Static("❯ ", id="input-prompt")
            yield Input(
                placeholder="Send command to OpenClaw...",
                id="command-input",
            )
            yield Static("", id="input-status")

    def on_mount(self) -> None:
        """Focus the input on mount if requested."""
        pass

    @on(Input.Submitted)
    def handle_submit(self, event: Input.Submitted) -> None:
        """Handle command submission."""
        command = event.value.strip()
        if not command:
            return

        # Add to history
        self._add_to_history(command)

        # Clear input
        input_widget = self.query_one("#command-input", Input)
        input_widget.value = ""

        # Send command
        self._send_command(command)

    def _add_to_history(self, command: str) -> None:
        """Add a command to history."""
        # Don't add duplicates of the last command
        if self._history and self._history[-1] == command:
            return

        self._history.append(command)

        # Trim history if too long
        if len(self._history) > MAX_HISTORY:
            self._history = self._history[-MAX_HISTORY:]

        # Reset history index
        self._history_index = len(self._history)
        self._current_input = ""

    def _send_command(self, command: str) -> None:
        """Send a command to OpenClaw."""
        self._set_status("sending", "⏳")
        self.add_class("sending")
        self.remove_class("error", "success")

        # Build the command
        cmd = ["openclaw", "agent", "--message", command, "--json"]

        if self._agent:
            cmd.extend(["--agent", self._agent])
        elif self._session_id:
            cmd.extend(["--session-id", self._session_id])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                self._set_status("success", "✓")
                self.remove_class("sending")
                self.add_class("success")

                # Parse response
                try:
                    data = json.loads(result.stdout)
                    response = data.get("content", data.get("response", result.stdout))
                except json.JSONDecodeError:
                    response = result.stdout

                # Emit message for app to handle
                self.post_message(CommandSent(command, str(response), True))

                # Clear status after delay
                self.set_timer(2.0, self._clear_status)
            else:
                error_msg = result.stderr or result.stdout or "Unknown error"
                self._set_status("error", "✗")
                self.remove_class("sending")
                self.add_class("error")
                self.post_message(CommandSent(command, error_msg, False))
                self.set_timer(3.0, self._clear_status)

        except subprocess.TimeoutExpired:
            self._set_status("error", "⏱")
            self.remove_class("sending")
            self.add_class("error")
            self.post_message(CommandSent(command, "Command timed out", False))
            self.set_timer(3.0, self._clear_status)

        except FileNotFoundError:
            self._set_status("error", "✗")
            self.remove_class("sending")
            self.add_class("error")
            self.post_message(CommandSent(command, "openclaw CLI not found", False))
            self.set_timer(3.0, self._clear_status)

        except Exception as e:
            self._set_status("error", "✗")
            self.remove_class("sending")
            self.add_class("error")
            self.post_message(CommandSent(command, str(e), False))
            self.set_timer(3.0, self._clear_status)

    def _set_status(self, status_type: str, icon: str) -> None:
        """Set the status indicator."""
        status = self.query_one("#input-status", Static)
        status.update(icon)

    def _clear_status(self) -> None:
        """Clear the status indicator."""
        self.remove_class("sending", "error", "success")
        status = self.query_one("#input-status", Static)
        status.update("")

    def action_history_prev(self) -> None:
        """Navigate to previous command in history."""
        if not self._history:
            return

        input_widget = self.query_one("#command-input", Input)

        # Save current input if at end of history
        if self._history_index == len(self._history):
            self._current_input = input_widget.value

        # Move back in history
        if self._history_index > 0:
            self._history_index -= 1
            input_widget.value = self._history[self._history_index]
            # Move cursor to end
            input_widget.cursor_position = len(input_widget.value)

    def action_history_next(self) -> None:
        """Navigate to next command in history."""
        if not self._history:
            return

        input_widget = self.query_one("#command-input", Input)

        # Move forward in history
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            input_widget.value = self._history[self._history_index]
        elif self._history_index == len(self._history) - 1:
            # Restore current input
            self._history_index = len(self._history)
            input_widget.value = self._current_input

        # Move cursor to end
        input_widget.cursor_position = len(input_widget.value)

    def action_blur_input(self) -> None:
        """Remove focus from the input."""
        self.app.set_focus(None)

    def focus_input(self) -> None:
        """Focus the command input."""
        input_widget = self.query_one("#command-input", Input)
        input_widget.focus()

    def set_agent(self, agent: str | None) -> None:
        """Set the target agent."""
        self._agent = agent

    def set_session_id(self, session_id: str | None) -> None:
        """Set the target session ID."""
        self._session_id = session_id

    @property
    def history(self) -> list[str]:
        """Get the command history."""
        return self._history.copy()
