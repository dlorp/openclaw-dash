"""Connection warning banner for degraded collector states."""

from textual.app import ComposeResult
from textual.widgets import Static

from openclaw_dash.collectors.base import get_collector_state

class ConnectionWarningBanner(Static):
    """Warning banner shown when collectors are in degraded/fallback state.
        Monitors all collector states and displays a prominent warning when:
    - Using stale/cached data due to connection failures
    - Circuit breaker is open
    - Collectors are returning fallback/default data
    
    This prevents silent degradation where users think the dashboard is
    working but are actually seeing zeros or stale data.
    """
        DEFAULT_CSS = """
    ConnectionWarningBanner {
        display: none;
        background: $warning;
        color: $text;
        text-align: center;
        height: 1;
        width: 100%;
        text-style: bold;
    }
        ConnectionWarningBanner.visible {
        display: block;
    }
    """
    
    # Collector names to monitor
    MONITORED_COLLECTORS = [
        "gateway",
        "sessions",         "agents",
        "cron",
        "repos",
        "activity",
        "channels",
        "alerts",
        "logs",
    ]
    
    def compose(self) -> ComposeResult:
        """Compose the warning banner."""
        yield Static("", id="warning-text")
    
    def check_and_update(self) -> None:
        """Check collector states and update warning display.
                Called during dashboard refresh cycles to check if any
        collectors are in a degraded state.
        """
        warnings: list[str] = []
        stale_collectors: list[str] = []
        circuit_open_collectors: list[str] = []
        error_collectors: list[str] = []
                for collector_name in self.MONITORED_COLLECTORS:
            state = get_collector_state(collector_name)
            if state is None:
                continue
                        # Check for various degraded states
            if state.state.value == "unavailable":
                error_collectors.append(collector_name)
            elif state.state.value == "error":
                error_collectors.append(collector_name)
            elif state.data.get("_circuit_open"):
                circuit_open_collectors.append(collector_name)
            elif state.data.get("_stale"):
                stale_collectors.append(collector_name)
        
        # Build warning message based on detected issues
        if circuit_open_collectors:
            warnings.append(f"WARNING: Circuit breaker open: {', '.join(circuit_open_collectors[:3])}")
        
        if error_collectors:
            # Focus on gateway since it's the most critical
            if "gateway" in error_collectors:
                warnings.append("WARNING: Gateway unreachable - using fallback data")
            elif len(error_collectors) <= 2:
                warnings.append(f"WARNING: Connection failed: {', '.join(error_collectors)}")
            else:
                warnings.append(f"WARNING: {len(error_collectors)} collectors unavailable")
        
        if stale_collectors and not warnings:
            # Only show stale warning if no more serious issues
            if len(stale_collectors) <= 2:
                warnings.append(f"WARNING: Using cached data: {', '.join(stale_collectors)}")
            else:
                warnings.append(f"WARNING: Using cached data ({len(stale_collectors)} sources)")
                # Update display
        if warnings:
            warning_text = " | ".join(warnings)
            self.query_one("#warning-text", Static).update(warning_text)
            self.add_class("visible")
        else:
            self.remove_class("visible")
        def on_mount(self) -> None:
        """Initial check on mount."""
        self.check_and_update()
