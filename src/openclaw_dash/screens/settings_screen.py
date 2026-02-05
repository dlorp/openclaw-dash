"""Settings screen with tabbed configuration sections.

A modal screen for configuring openclaw-dash settings, organized into
tabbed sections: General, Tools, Appearance, Keybinds, and Models.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from textual import on, work
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

from openclaw_dash.services.model_discovery import (
    DiscoveryResult,
    ModelDiscoveryService,
    ModelTier,
)
from openclaw_dash.settings_manager import SettingsManager

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
# Settings Screen
# =============================================================================


class SettingsScreen(ModalScreen[bool]):
    """Modal screen for application settings.

    Returns True if settings were saved, False if cancelled.
    """

    BINDINGS: ClassVar[list[Binding | tuple[str, str, str]]] = [
        Binding("escape", "cancel", "Cancel", priority=True),
        Binding("ctrl+s", "save", "Save", priority=True),
        Binding("1", "tab_general", "General", show=False),
        Binding("2", "tab_tools", "Tools", show=False),
        Binding("3", "tab_appearance", "Appearance", show=False),
        Binding("4", "tab_keybinds", "Keybinds", show=False),
        Binding("5", "tab_models", "Models", show=False),
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
        height: auto;
        background: $surface;
        color: $primary;
        content-align: center middle;
        text-style: bold;
        padding: 0;
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

    /* Models tab styles */
    #model-discovery-stats {
        height: auto;
        padding: 1;
        background: $surface-darken-1;
        border: solid $primary-darken-3;
        margin: 1 0;
    }

    .tier-stat {
        height: auto;
        padding: 0 1;
    }

    .tier-stat Label {
        width: auto;
    }

    #btn-scan-models {
        margin: 1 0;
    }
    """

    def __init__(self, settings_manager: SettingsManager | None = None, **kwargs) -> None:
        """Initialize settings screen.

        Args:
            settings_manager: Optional settings manager instance. If None, creates a new one.
        """
        super().__init__(**kwargs)
        self._dirty = False  # Track if settings have been modified
        self._errors: dict[str, str] = {}  # Field validation errors
        self._discovered_models: DiscoveryResult | None = None
        self._settings = settings_manager or SettingsManager()

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-container"):
            yield Static(
                "╔════════════════════════════════════════════════════════════════════════════╗\n"
                "║                                Settings                                  ║\n"
                "╚════════════════════════════════════════════════════════════════════════════╝",
                id="settings-header",
            )

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
                                    [(name, name) for name in ["dark", "light", "phosphor"]],
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

                    # =========================================================
                    # Models Tab
                    # =========================================================
                    with TabPane("Models", id="models"):
                        with VerticalScroll(classes="tab-content"):
                            yield Static("Model Sources", classes="section-header")

                            with Horizontal(classes="setting-row"):
                                yield Label("Enable HuggingFace cache scanning")
                                yield Switch(value=True, id="setting-hf-cache-scan")

                            with Horizontal(classes="setting-row"):
                                yield Label("Enable Ollama scanning")
                                yield Switch(value=True, id="setting-ollama-scan")

                            with Horizontal(classes="setting-row"):
                                yield Label("Custom model paths")
                                yield Input(
                                    value="",
                                    id="setting-custom-model-paths",
                                    placeholder="comma-separated paths",
                                )

                            yield Static("Default Models", classes="section-header")

                            with Horizontal(classes="setting-row"):
                                yield Label("▸ Default FAST tier model")
                                yield Select(
                                    [("(none)", "")],
                                    value="",
                                    id="setting-default-fast-model",
                                    allow_blank=True,
                                )

                            with Horizontal(classes="setting-row"):
                                yield Label("◉ Default BALANCED tier model")
                                yield Select(
                                    [("(none)", "")],
                                    value="",
                                    id="setting-default-balanced-model",
                                    allow_blank=True,
                                )

                            with Horizontal(classes="setting-row"):
                                yield Label("★ Default POWERFUL tier model")
                                yield Select(
                                    [("(none)", "")],
                                    value="",
                                    id="setting-default-powerful-model",
                                    allow_blank=True,
                                )

                            yield Static("Discovery", classes="section-header")

                            yield Button(
                                "› Scan for Models",
                                variant="primary",
                                id="btn-scan-models",
                            )

                            with Vertical(id="model-discovery-stats"):
                                yield Static(
                                    "No scan performed yet. Click 'Scan for Models' to discover local LLMs.",
                                    id="discovery-status",
                                )
                                with Horizontal(classes="tier-stat"):
                                    yield Label("▸ FAST:", id="tier-fast-label")
                                    yield Label("—", id="tier-fast-count")
                                with Horizontal(classes="tier-stat"):
                                    yield Label("◉ BALANCED:", id="tier-balanced-label")
                                    yield Label("—", id="tier-balanced-count")
                                with Horizontal(classes="tier-stat"):
                                    yield Label("★ POWERFUL:", id="tier-powerful-label")
                                    yield Label("—", id="tier-powerful-count")

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
        """Load settings from config into form fields."""
        # Map settings keys to widget IDs and their types
        input_mappings = {
            "general.refresh_interval": "setting-refresh-interval",
            "gateway.host": "setting-gateway-host",
            "gateway.port": "setting-gateway-port",
            "tools.default_timeout": "setting-tool-timeout",
            "models.custom_paths": "setting-custom-model-paths",
        }

        switch_mappings = {
            "general.show_notifications": "setting-notifications",
            "gateway.auto_connect": "setting-auto-connect",
            "tools.confirm_dangerous": "setting-confirm-dangerous",
            "tools.log_calls": "setting-log-tools",
            "tools.allow_writes": "setting-allow-writes",
            "tools.allow_shell": "setting-allow-shell",
            "tools.allow_network": "setting-allow-network",
            "appearance.show_clock": "setting-show-clock",
            "appearance.show_resources": "setting-show-resources",
            "appearance.compact_mode": "setting-compact-mode",
            "appearance.high_contrast": "setting-high-contrast",
            "appearance.reduce_animations": "setting-reduce-animations",
            "models.hf_cache_scan": "setting-hf-cache-scan",
            "models.ollama_scan": "setting-ollama-scan",
        }

        select_mappings = {
            "appearance.theme": "setting-theme",
        }

        keybind_mappings = {
            "keybinds.refresh": "keybind-refresh",
            "keybinds.theme": "keybind-theme",
            "keybinds.help": "keybind-help",
            "keybinds.quit": "keybind-quit",
            "keybinds.input": "keybind-input",
            "keybinds.jump": "keybind-jump",
            "keybinds.gateway": "keybind-gateway",
            "keybinds.alerts": "keybind-alerts",
            "keybinds.logs": "keybind-logs",
            "keybinds.security": "keybind-security",
        }

        # Load Input values
        for settings_key, widget_id in input_mappings.items():
            try:
                value = self._settings.get(settings_key)
                if value is not None:
                    input_widget = self.query_one(f"#{widget_id}", Input)
                    input_widget.value = str(value)
            except Exception:
                pass

        # Load Switch values
        for settings_key, widget_id in switch_mappings.items():
            try:
                value = self._settings.get(settings_key)
                if value is not None:
                    switch = self.query_one(f"#{widget_id}", Switch)
                    switch.value = bool(value)
            except Exception:
                pass

        # Load Select values
        for settings_key, widget_id in select_mappings.items():
            try:
                value = self._settings.get(settings_key)
                if value is not None:
                    select = self.query_one(f"#{widget_id}", Select)
                    select.value = str(value)
            except Exception:
                pass

        # Load keybinds
        for settings_key, widget_id in keybind_mappings.items():
            try:
                value = self._settings.get(settings_key)
                if value is not None:
                    input_widget = self.query_one(f"#{widget_id}", Input)
                    input_widget.value = str(value)
            except Exception:
                pass

        # Reset dirty flag after loading
        self._dirty = False

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

    @on(Button.Pressed, "#btn-scan-models")
    def on_scan_models_pressed(self) -> None:
        """Handle scan models button press."""
        self._scan_for_models()

    @work(exclusive=True)
    async def _scan_for_models(self) -> None:
        """Scan for local models in background."""
        # Update UI to show scanning
        status_label = self.query_one("#discovery-status", Static)
        status_label.update(" Scanning for models...")

        scan_button = self.query_one("#btn-scan-models", Button)
        scan_button.disabled = True

        try:
            # Get custom paths from settings
            custom_paths_input = self.query_one("#setting-custom-model-paths", Input)
            custom_paths_str = custom_paths_input.value.strip()
            custom_paths = []
            if custom_paths_str:
                custom_paths = [Path(p.strip()) for p in custom_paths_str.split(",") if p.strip()]

            # Check scan settings
            hf_enabled = self.query_one("#setting-hf-cache-scan", Switch).value
            ollama_enabled = self.query_one("#setting-ollama-scan", Switch).value

            # Create service and scan
            service = ModelDiscoveryService(custom_paths=custom_paths)
            result = service.discover()

            # Filter results based on settings
            if not hf_enabled:
                result.models = [m for m in result.models if m.source != "huggingface"]
            if not ollama_enabled:
                result.models = [m for m in result.models if m.source != "ollama"]

            self._discovered_models = result

            # Update UI with results
            self._update_model_discovery_ui(result)

        except Exception as e:
            status_label.update(f"✗ Scan failed: {e}")
        finally:
            scan_button.disabled = False

    def _update_model_discovery_ui(self, result: DiscoveryResult) -> None:
        """Update UI with model discovery results."""
        # Update status
        status_label = self.query_one("#discovery-status", Static)
        total = len(result.models)
        paths_scanned = len(result.scan_paths)
        status_label.update(f"✓ Found {total} model(s) across {paths_scanned} path(s)")

        # Update tier counts
        by_tier = result.by_tier
        fast_count = len(by_tier[ModelTier.FAST])
        balanced_count = len(by_tier[ModelTier.BALANCED])
        powerful_count = len(by_tier[ModelTier.POWERFUL])

        self.query_one("#tier-fast-count", Label).update(str(fast_count))
        self.query_one("#tier-balanced-count", Label).update(str(balanced_count))
        self.query_one("#tier-powerful-count", Label).update(str(powerful_count))

        # Update model selectors with discovered models
        self._populate_model_selects(result)

    def _populate_model_selects(self, result: DiscoveryResult) -> None:
        """Populate model select dropdowns with discovered models."""
        by_tier = result.by_tier

        # Build options for each tier
        def make_options(models):
            options = [("(none)", "")]
            for model in models:
                display = f"{model.tier_emoji} {model.display_name} ({model.quantization})"
                options.append((display, str(model.path)))
            return options

        # Update FAST selector
        fast_select = self.query_one("#setting-default-fast-model", Select)
        fast_options = make_options(by_tier[ModelTier.FAST])
        fast_select.set_options(fast_options)

        # Update BALANCED selector
        balanced_select = self.query_one("#setting-default-balanced-model", Select)
        balanced_options = make_options(by_tier[ModelTier.BALANCED])
        balanced_select.set_options(balanced_options)

        # Update POWERFUL selector
        powerful_select = self.query_one("#setting-default-powerful-model", Select)
        powerful_options = make_options(by_tier[ModelTier.POWERFUL])
        powerful_select.set_options(powerful_options)

    def action_save(self) -> None:
        """Validate and save settings."""
        if not self._validate_all():
            self.app.notify(
                "Please fix validation errors before saving",
                severity="error",
                timeout=3.0,
            )
            return

        collected = self._collect_settings()

        # Map collected settings keys to SettingsManager paths
        key_mappings = {
            # General settings
            "refresh-interval": "general.refresh_interval",
            "gateway-host": "gateway.host",
            "gateway-port": "gateway.port",
            "notifications": "general.show_notifications",
            "auto-connect": "gateway.auto_connect",
            # Tool settings
            "tool-timeout": "tools.default_timeout",
            "confirm-dangerous": "tools.confirm_dangerous",
            "log-tools": "tools.log_calls",
            "allow-writes": "tools.allow_writes",
            "allow-shell": "tools.allow_shell",
            "allow-network": "tools.allow_network",
            # Appearance settings
            "theme": "appearance.theme",
            "show-clock": "appearance.show_clock",
            "show-resources": "appearance.show_resources",
            "compact-mode": "appearance.compact_mode",
            "high-contrast": "appearance.high_contrast",
            "reduce-animations": "appearance.reduce_animations",
            # Model settings
            "hf-cache-scan": "models.hf_cache_scan",
            "ollama-scan": "models.ollama_scan",
            "custom-model-paths": "models.custom_paths",
            "default-fast-model": "models.default_fast",
            "default-balanced-model": "models.default_balanced",
            "default-powerful-model": "models.default_powerful",
            # Keybinds
            "keybind_refresh": "keybinds.refresh",
            "keybind_theme": "keybinds.theme",
            "keybind_help": "keybinds.help",
            "keybind_quit": "keybinds.quit",
            "keybind_input": "keybinds.input",
            "keybind_jump": "keybinds.jump",
            "keybind_gateway": "keybinds.gateway",
            "keybind_alerts": "keybinds.alerts",
            "keybind_logs": "keybinds.logs",
            "keybind_security": "keybinds.security",
        }

        # Apply settings to manager
        for collected_key, value in collected.items():
            if collected_key in key_mappings:
                settings_path = key_mappings[collected_key]
                # Convert numeric strings to int for integer settings
                if collected_key in ("refresh-interval", "gateway-port", "tool-timeout"):
                    try:
                        value = int(value) if value else None
                    except (ValueError, TypeError):
                        pass
                self._settings.set(settings_path, value)

        # Save to file
        try:
            self._settings.save()
            self.app.notify("Settings saved!", timeout=2.0)
            self.dismiss(True)
        except OSError as e:
            self.app.notify(
                f"Failed to save settings: {e}",
                severity="error",
                timeout=4.0,
            )

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
            "setting-custom-model-paths": "",
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
            "setting-hf-cache-scan": True,
            "setting-ollama-scan": True,
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

        # Reset model selects
        for select_id in [
            "setting-default-fast-model",
            "setting-default-balanced-model",
            "setting-default-powerful-model",
        ]:
            try:
                model_select = self.query_one(f"#{select_id}", Select)
                model_select.value = ""
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

    def action_tab_general(self) -> None:
        """Switch to General tab."""
        self.query_one(TabbedContent).active = "general"

    def action_tab_tools(self) -> None:
        """Switch to Tools tab."""
        self.query_one(TabbedContent).active = "tools"

    def action_tab_appearance(self) -> None:
        """Switch to Appearance tab."""
        self.query_one(TabbedContent).active = "appearance"

    def action_tab_keybinds(self) -> None:
        """Switch to Keybinds tab."""
        self.query_one(TabbedContent).active = "keybinds"

    def action_tab_models(self) -> None:
        """Switch to Models tab."""
        self.query_one(TabbedContent).active = "models"
