"""Command palette provider for the dashboard.

Provides quick actions accessible via Ctrl+P command palette.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from textual.command import DiscoveryHit, Hit, Hits, Provider

from openclaw_dash.collectors import activity, cron, gateway, repos, sessions
from openclaw_dash.themes import THEME_NAMES

if TYPE_CHECKING:
    from openclaw_dash.app import DashboardApp


class DashboardCommands(Provider):
    """Command provider for dashboard actions."""

    @property
    def app(self) -> DashboardApp:
        """Get the app instance."""
        return self.screen.app  # type: ignore

    async def discover(self) -> Hits:
        """Provide discoverable commands shown before user input."""
        # Core actions
        yield DiscoveryHit(
            "Refresh",
            self.app.action_refresh,
            help="Refresh all dashboard panels (r)",
        )
        yield DiscoveryHit(
            "Cycle Theme",
            self.app.action_cycle_theme,
            help="Switch to next theme (t)",
        )
        yield DiscoveryHit(
            "Help",
            self.app.action_help,
            help="Show keyboard shortcuts (h)",
        )
        yield DiscoveryHit(
            "Export Data",
            self._export_data,
            help="Export dashboard data to JSON",
        )
        yield DiscoveryHit(
            "Toggle Help",
            self.app.action_help,
            help="Show/hide keyboard shortcuts (h/?)",
        )
        yield DiscoveryHit(
            "Toggle Resources",
            self._toggle_resources,
            help="Show/hide resources panel (x)",
        )
        yield DiscoveryHit(
            "Quit",
            self.app.action_quit,
            help="Exit the application (q)",
        )

        # Theme selection
        for theme_name in THEME_NAMES:
            yield DiscoveryHit(
                f"Theme: {theme_name.title()}",
                lambda t=theme_name: self._set_theme(t),
                help=f"Switch to {theme_name} theme",
            )

        # Focus panels
        panels = [
            ("Gateway", "gateway-panel", "g"),
            ("Security", "security-panel", "s"),
            ("Metrics", "metrics-panel", "m"),
            ("Alerts", "alerts-panel", "a"),
            ("Cron", "cron-panel", "c"),
            ("Repos", "repos-panel", "p"),
            ("Logs", "logs-panel", "l"),
            ("Resources", "resources-panel", "x"),
            ("Sessions", "sessions-panel", ""),
            ("Channels", "channels-panel", ""),
            ("Activity", "activity-panel", ""),
            ("Current Task", "task-panel", ""),
        ]
        for name, panel_id, key in panels:
            shortcut = f" ({key})" if key else ""
            yield DiscoveryHit(
                f"Focus: {name}",
                lambda pid=panel_id: self.app.action_focus_panel(pid),
                help=f"Focus the {name} panel{shortcut}",
            )

    async def search(self, query: str) -> Hits:
        """Search for commands matching the query."""
        matcher = self.matcher(query)

        # Core actions
        commands = [
            ("Refresh All Panels", self.app.action_refresh, "Refresh dashboard data"),
            ("Cycle Theme", self.app.action_cycle_theme, "Switch to next theme"),
            ("Show Help", self.app.action_help, "Display keyboard shortcuts"),
            ("Export Dashboard Data", self._export_data, "Save data to JSON file"),
            ("Quit Application", self.app.action_quit, "Exit the dashboard"),
        ]

        for name, callback, help_text in commands:
            match = matcher.match(name)
            if match > 0:
                yield Hit(match, name, callback, help=help_text)

        # Theme commands
        for theme_name in THEME_NAMES:
            name = f"Set Theme: {theme_name.title()}"
            match = matcher.match(name)
            if match > 0:
                yield Hit(
                    match,
                    name,
                    lambda t=theme_name: self._set_theme(t),
                    help=f"Switch to {theme_name} theme",
                )

        # Toggle resources command
        toggle_res_name = "Toggle Resources Panel"
        match = matcher.match(toggle_res_name)
        if match > 0:
            yield Hit(match, toggle_res_name, self._toggle_resources, help="Show/hide resources (x)")

        # Focus panel commands
        panels = [
            ("Gateway Panel", "gateway-panel"),
            ("Security Panel", "security-panel"),
            ("Metrics Panel", "metrics-panel"),
            ("Alerts Panel", "alerts-panel"),
            ("Cron Panel", "cron-panel"),
            ("Repos Panel", "repos-panel"),
            ("Logs Panel", "logs-panel"),
            ("Resources Panel", "resources-panel"),
            ("Sessions Panel", "sessions-panel"),
            ("Channels Panel", "channels-panel"),
            ("Activity Panel", "activity-panel"),
            ("Task Panel", "task-panel"),
        ]
        for name, panel_id in panels:
            full_name = f"Focus {name}"
            match = matcher.match(full_name)
            if match > 0:
                yield Hit(
                    match,
                    full_name,
                    lambda pid=panel_id: self.app.action_focus_panel(pid),
                    help=f"Focus the {name}",
                )

    def _set_theme(self, theme_name: str) -> None:
        """Set a specific theme and save preference."""
        self.app.theme = theme_name
        self.app.config.update(theme=theme_name)
        self.app.notify(f"Theme: {theme_name}", timeout=1.5)

    def _toggle_resources(self) -> None:
        """Toggle the resources panel visibility."""
        self.app.action_toggle_resources()

    def _export_data(self) -> None:
        """Export dashboard data to JSON."""
        data = {
            "exported_at": datetime.now().isoformat(),
            "gateway": gateway.collect(),
            "activity": activity.collect(),
            "repos": repos.collect(),
            "cron": cron.collect(),
            "sessions": sessions.collect(),
        }

        # Export to home directory
        export_path = Path.home() / "openclaw-dash-export.json"
        with open(export_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        self.app.notify(f"Exported to {export_path}", timeout=3)
