"""Settings screen with tabbed configuration sections.

A modal screen for configuring openclaw-dash settings, organized into
tabbed sections: General, Tools, Appearance, and Keybinds.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.validation import Length, ValidationResult, Validator
from textual.widgets import (
    Button,
    Footer,
    Input,
    Label,
    Select,
    Static,
    Switch,
    TabbedContent,
    TabPane,
)

# =============================================================================
# Validators
# =============================================================================


class PositiveInteger(Validator):
    """Validates that input is a positive integer."""

    def validate(self, value: str) -> ValidationResult:
        """Check if value is a positive integer."""
        if not value:
            return self.success()
        try:
            num = int(value)
            if num <= 0:
                return self.failure("Must be a positive number")
            return self.success()
        except ValueError:
            return self.failure("Must be a valid number")


class PortNumber(Validator):
    """Validates that input is a valid port number (1-65535)."""

    def validate(self, value: str) -> ValidationResult:
        """Check if value is a valid port number."""
        if not value:
            return self.success()
        try:
            port = int(value)
            if port < 1 or port > 65535:
                return self.failure("Port must be between 1 and 65535")
            return self.success()
        except ValueError:
            return self.failure("Must be a valid port number")


# =============================================================================
# Messages
# =============================================================================


@dataclass
class SettingsSaved:
    """Posted when settings are saved."""

    pass


@dataclass
class SettingsReset:
    """Posted when settings are reset to defaults."""

    pass


# =============================================================================
# Form Field Widget
# =============================================================================


class FormField(Vertical):
    """A labeled form field with optional help text and error display."""

    DEFAULT_CSS = """
    FormField {
        height: auto;
        margin-bottom: 1;
    }

    FormField > Label {
        margin-bottom: 0;
    }

    FormField > .help-text {
        color: $text-muted;
        text-style: italic;
    }

    FormField > .error-text {
        color: $error;
        text-style: bold;
    }

    FormField Input {
        width: 100%;
    }

    FormField Select {
        width: 100%;
    }
    """

    def __init__(
        self,
        label: str,
        field_id: str,
        help_text: str = "",
        **kwargs,
    ) -> None:
        """Initialize form field.

        Args:
            label: The label text for the field.
            field_id: ID for the field (used for the input/switch/select widget).
            help_text: Optional help text shown below the field.
            **kwargs: Additional arguments passed to Vertical.
        """
        super().__init__(**kwargs)
        self._label = label
        self._field_id = field_id
        self._help_text = help_text

    def compose(self) -> ComposeResult:
        yield Label(self._label)
        # Children will be mounted by subclasses
        if self._help_text:
            yield Static(self._help_text, classes="help-text")

    def show_error(self, message: str) -> None:
        """Display an error message."""
        # Remove existing error if any
        self.hide_error()
        error = Static(f"⚠️ {message}", classes="error-text")
        error.id = f"{self._field_id}-error"
        self.mount(error)

    def hide_error(self) -> None:
        """Hide the error message if displayed."""
        try:
            error = self.query_one(f"#{self._field_id}-error")
            error.remove()
        except Exception:
            pass


# =============================================================================
# Settings Screen
# =============================================================================


class SettingsScreen(ModalScreen[bool]):
    """Modal screen for application settings.

    Returns True if settings were saved, False if cancelled.
    """

    BINDINGS: ClassVar[list[Binding | tuple[str, str, str]]] = [
        Binding("escape", "cancel", "Cancel", priority=True),
        Binding("ctrl+s", "save", "Save", priority=True),
    ]

    CSS = """
    SettingsScreen {
        align: center middle;
    }

    #settings-container {
        width: 80;
        height: 90%;
        max-width: 100;
        background: $surface;
        border: thick $primary;
    }

    #settings-header {
        dock: top;
        height: 3;
        background: $primary;
        color: $background;
        content-align: center middle;
        text-style: bold;
        padding: 1;
    }

    #settings-content {
        height: 1fr;
        padding: 1 2;
    }

    #settings-footer {
        dock: bottom;
        height: auto;
        padding: 1 2;
        background: $surface;
        border-top: solid $primary-darken-2;
    }

    #button-row {
        align: right middle;
        height: auto;
    }

    #button-row Button {
        margin-left: 1;
    }

    .tab-content {
        padding: 1;
        height: 100%;
    }

    .section-header {
        text-style: bold;
        color: $primary;
        padding: 1 0;
        border-bottom: solid $primary-darken-3;
        margin-bottom: 1;
    }

    .setting-row {
        height: auto;
        padding: 0 0 1 0;
    }

    .setting-row Label {
        width: 30;
    }

    .setting-row Switch {
        margin-left: 1;
    }

    .setting-row Input {
        width: 40;
    }

    .setting-row Select {
        width: 40;
    }

    #keybinds-table {
        height: auto;
        padding: 1;
    }

    .keybind-row {
        height: auto;
        padding: 0 0 1 0;
    }

    .keybind-row Label {
        width: 25;
    }

    .keybind-row Input {
        width: 20;
    }
    """

    def __init__(self, **kwargs) -> None:
        """Initialize settings screen."""
        super().__init__(**kwargs)
        self._dirty = False  # Track if settings have been modified
        self._errors: dict[str, str] = {}  # Field validation errors

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-container"):
            yield Static("⚙️  Settings", id="settings-header")

            with VerticalScroll(id="settings-content"):
                with TabbedContent(initial="general"):
                    # =========================================================
                    # General Tab
                    # =========================================================
                    with TabPane("General", id="general"):
                        with VerticalScroll(classes="tab-content"):
                            yield Static("Dashboard Settings", classes="section-header")

                            with Horizontal(classes="setting-row"):
                                yield Label("Refresh interval (seconds)")
                                yield Input(
                                    value="30",
                                    id="setting-refresh-interval",
                                    validators=[PositiveInteger()],
                                    type="integer",
                                )

                            with Horizontal(classes="setting-row"):
                                yield Label("Show notifications")
                                yield Switch(value=True, id="setting-notifications")

                            with Horizontal(classes="setting-row"):
                                yield Label("Auto-connect on startup")
                                yield Switch(value=True, id="setting-auto-connect")

                            yield Static("Gateway Settings", classes="section-header")

                            with Horizontal(classes="setting-row"):
                                yield Label("Gateway host")
                                yield Input(
                                    value="localhost",
                                    id="setting-gateway-host",
                                    validators=[Length(minimum=1)],
                                )

                            with Horizontal(classes="setting-row"):
                                yield Label("Gateway port")
                                yield Input(
                                    value="18789",
                                    id="setting-gateway-port",
                                    validators=[PortNumber()],
                                    type="integer",
                                )

                    # =========================================================
                    # Tools Tab
                    # =========================================================
                    with TabPane("Tools", id="tools"):
                        with VerticalScroll(classes="tab-content"):
                            yield Static("Tool Execution", classes="section-header")

                            with Horizontal(classes="setting-row"):
                                yield Label("Default timeout (seconds)")
                                yield Input(
                                    value="30",
                                    id="setting-tool-timeout",
                                    validators=[PositiveInteger()],
                                    type="integer",
                                )

                            with Horizontal(classes="setting-row"):
                                yield Label("Confirm dangerous tools")
                                yield Switch(value=True, id="setting-confirm-dangerous")

                            with Horizontal(classes="setting-row"):
                                yield Label("Log tool calls")
                                yield Switch(value=True, id="setting-log-tools")

                            yield Static("Tool Permissions", classes="section-header")

                            with Horizontal(classes="setting-row"):
                                yield Label("Allow file writes")
                                yield Switch(value=True, id="setting-allow-writes")

                            with Horizontal(classes="setting-row"):
                                yield Label("Allow shell commands")
                                yield Switch(value=True, id="setting-allow-shell")

                            with Horizontal(classes="setting-row"):
                                yield Label("Allow network access")
                                yield Switch(value=True, id="setting-allow-network")

                    # =========================================================
                    # Appearance Tab
                    # =========================================================
                    with TabPane("Appearance", id="appearance"):
                        with VerticalScroll(classes="tab-content"):
                            yield Static("Theme", classes="section-header")

                            with Horizontal(classes="setting-row"):
                                yield Label("Color theme")
                                yield Select(
                                    [(name, name) for name in ["dark", "light", "hacker"]],
                                    value="dark",
                                    id="setting-theme",
                                )

                            with Horizontal(classes="setting-row"):
                                yield Label("Show clock in header")
                                yield Switch(value=True, id="setting-show-clock")

                            yield Static("Layout", classes="section-header")

                            with Horizontal(classes="setting-row"):
                                yield Label("Show resources panel")
                                yield Switch(value=False, id="setting-show-resources")

                            with Horizontal(classes="setting-row"):
                                yield Label("Compact mode")
                                yield Switch(value=False, id="setting-compact-mode")

                            yield Static("Accessibility", classes="section-header")

                            with Horizontal(classes="setting-row"):
                                yield Label("High contrast")
                                yield Switch(value=False, id="setting-high-contrast")

                            with Horizontal(classes="setting-row"):
                                yield Label("Reduce animations")
                                yield Switch(value=False, id="setting-reduce-animations")

                    # =========================================================
                    # Keybinds Tab
                    # =========================================================
                    with TabPane("Keybinds", id="keybinds"):
                        with VerticalScroll(classes="tab-content"):
                            yield Static("Navigation", classes="section-header")

                            with Vertical(id="keybinds-table"):
                                with Horizontal(classes="keybind-row"):
                                    yield Label("Refresh panels")
                                    yield Input(value="r", id="keybind-refresh")

                                with Horizontal(classes="keybind-row"):
                                    yield Label("Cycle theme")
                                    yield Input(value="t", id="keybind-theme")

                                with Horizontal(classes="keybind-row"):
                                    yield Label("Show help")
                                    yield Input(value="h", id="keybind-help")

                                with Horizontal(classes="keybind-row"):
                                    yield Label("Quit")
                                    yield Input(value="q", id="keybind-quit")

                                with Horizontal(classes="keybind-row"):
                                    yield Label("Focus input")
                                    yield Input(value=":", id="keybind-input")

                                with Horizontal(classes="keybind-row"):
                                    yield Label("Jump mode")
                                    yield Input(value="f", id="keybind-jump")

                            yield Static("Panel Focus", classes="section-header")

                            with Vertical():
                                with Horizontal(classes="keybind-row"):
                                    yield Label("Focus gateway")
                                    yield Input(value="g", id="keybind-gateway")

                                with Horizontal(classes="keybind-row"):
                                    yield Label("Focus alerts")
                                    yield Input(value="a", id="keybind-alerts")

                                with Horizontal(classes="keybind-row"):
                                    yield Label("Focus logs")
                                    yield Input(value="l", id="keybind-logs")

                                with Horizontal(classes="keybind-row"):
                                    yield Label("Focus security")
                                    yield Input(value="s", id="keybind-security")

            # Footer with action buttons
            with Horizontal(id="settings-footer"):
                with Horizontal(id="button-row"):
                    yield Button("Reset", variant="default", id="btn-reset")
                    yield Button("Cancel", variant="default", id="btn-cancel")
                    yield Button("Save", variant="primary", id="btn-save")

        yield Footer()

    def on_mount(self) -> None:
        """Load current settings when mounted."""
        self._load_settings()

    def _load_settings(self) -> None:
        """Load settings from config into form fields.

        TODO: Wire this up to SettingsManager when available.
        """
        # For now, this is a skeleton - values are set in compose()
        pass

    def _collect_settings(self) -> dict:
        """Collect all settings from form fields.

        Returns:
            Dictionary of setting names to values.
        """
        settings = {}

        # Collect Input values
        for input_widget in self.query(Input):
            if input_widget.id and input_widget.id.startswith("setting-"):
                key = input_widget.id.replace("setting-", "")
                settings[key] = input_widget.value

        # Collect Switch values
        for switch in self.query(Switch):
            if switch.id and switch.id.startswith("setting-"):
                key = switch.id.replace("setting-", "")
                settings[key] = switch.value

        # Collect Select values
        for select in self.query(Select):
            if select.id and select.id.startswith("setting-"):
                key = select.id.replace("setting-", "")
                settings[key] = select.value

        # Collect keybinds
        for input_widget in self.query(Input):
            if input_widget.id and input_widget.id.startswith("keybind-"):
                key = input_widget.id.replace("keybind-", "")
                settings[f"keybind_{key}"] = input_widget.value

        return settings

    def _validate_all(self) -> bool:
        """Validate all form fields.

        Returns:
            True if all fields are valid, False otherwise.
        """
        self._errors.clear()
        all_valid = True

        for input_widget in self.query(Input):
            if not input_widget.is_valid:
                all_valid = False
                if input_widget.id:
                    # Get validation message
                    result = input_widget.validate(input_widget.value)
                    if result and result.failure_descriptions:
                        self._errors[input_widget.id] = result.failure_descriptions[0]

        return all_valid

    @on(Input.Changed)
    def on_input_changed(self, event: Input.Changed) -> None:
        """Mark settings as dirty when input changes."""
        self._dirty = True

        # Validate the input and show/hide error
        if event.input.id:
            result = event.input.validate(event.value)
            if result and not result.is_valid and result.failure_descriptions:
                # Find parent FormField if any, otherwise show in notification
                self.app.notify(
                    result.failure_descriptions[0],
                    severity="warning",
                    timeout=2.0,
                )

    @on(Switch.Changed)
    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Mark settings as dirty when switch changes."""
        self._dirty = True

    @on(Select.Changed)
    def on_select_changed(self, event: Select.Changed) -> None:
        """Mark settings as dirty when select changes."""
        self._dirty = True

    @on(Button.Pressed, "#btn-save")
    def on_save_pressed(self) -> None:
        """Handle save button press."""
        self.action_save()

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel_pressed(self) -> None:
        """Handle cancel button press."""
        self.action_cancel()

    @on(Button.Pressed, "#btn-reset")
    def on_reset_pressed(self) -> None:
        """Handle reset button press."""
        self.action_reset()

    def action_save(self) -> None:
        """Validate and save settings."""
        if not self._validate_all():
            self.app.notify(
                "Please fix validation errors before saving",
                severity="error",
                timeout=3.0,
            )
            return

        _settings = self._collect_settings()  # noqa: F841

        # TODO: Actually save settings via SettingsManager
        # Will use _settings when wired up
        self.app.notify("Settings saved!", timeout=2.0)
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancel and close without saving."""
        if self._dirty:
            # Could show confirmation dialog, but for now just dismiss
            pass
        self.dismiss(False)

    def action_reset(self) -> None:
        """Reset all settings to defaults."""
        # Reset Input fields
        defaults = {
            "setting-refresh-interval": "30",
            "setting-gateway-host": "localhost",
            "setting-gateway-port": "18789",
            "setting-tool-timeout": "30",
        }

        for input_id, default_value in defaults.items():
            try:
                input_widget = self.query_one(f"#{input_id}", Input)
                input_widget.value = default_value
            except Exception:
                pass

        # Reset Switch fields to defaults
        switch_defaults = {
            "setting-notifications": True,
            "setting-auto-connect": True,
            "setting-confirm-dangerous": True,
            "setting-log-tools": True,
            "setting-allow-writes": True,
            "setting-allow-shell": True,
            "setting-allow-network": True,
            "setting-show-clock": True,
            "setting-show-resources": False,
            "setting-compact-mode": False,
            "setting-high-contrast": False,
            "setting-reduce-animations": False,
        }

        for switch_id, default_value in switch_defaults.items():
            try:
                switch = self.query_one(f"#{switch_id}", Switch)
                switch.value = default_value
            except Exception:
                pass

        # Reset Select fields
        try:
            theme_select = self.query_one("#setting-theme", Select)
            theme_select.value = "dark"
        except Exception:
            pass

        # Reset keybinds
        keybind_defaults = {
            "keybind-refresh": "r",
            "keybind-theme": "t",
            "keybind-help": "h",
            "keybind-quit": "q",
            "keybind-input": ":",
            "keybind-jump": "f",
            "keybind-gateway": "g",
            "keybind-alerts": "a",
            "keybind-logs": "l",
            "keybind-security": "s",
        }

        for keybind_id, default_value in keybind_defaults.items():
            try:
                input_widget = self.query_one(f"#{keybind_id}", Input)
                input_widget.value = default_value
            except Exception:
                pass

        self._dirty = True
        self.app.notify("Settings reset to defaults", timeout=2.0)
