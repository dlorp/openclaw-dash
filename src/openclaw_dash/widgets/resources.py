"""System resources panel widget for the TUI dashboard."""

from textual.app import ComposeResult
from textual.widgets import Static

from openclaw_dash.collectors import resources
from openclaw_dash.widgets.ascii_art import (
    STATUS_SYMBOLS,
    mini_bar,
    progress_bar,
    separator,
    sparkline,
    status_indicator,
)

# History tracking for sparklines
_cpu_history: list[float] = []
_mem_history: list[float] = []
_net_sent_history: list[float] = []
_net_recv_history: list[float] = []
MAX_HISTORY = 30


def _format_bytes(n: float, suffix: str = "B") -> str:
    """Format bytes into human-readable string."""
    for unit in ["", "K", "M", "G", "T"]:
        if abs(n) < 1024:
            return f"{n:.1f}{unit}{suffix}"
        n /= 1024
    return f"{n:.1f}P{suffix}"


def _format_rate(bps: float) -> str:
    """Format bytes per second into human-readable rate."""
    if bps < 1024:
        return f"{bps:.0f} B/s"
    elif bps < 1024 * 1024:
        return f"{bps / 1024:.1f} KB/s"
    else:
        return f"{bps / (1024 * 1024):.1f} MB/s"


class ResourcesPanel(Static):
    """System resources monitoring panel."""

    def compose(self) -> ComposeResult:
        yield Static("Loading...", id="resources-content")

    def refresh_data(self) -> None:
        global _cpu_history, _mem_history, _net_sent_history, _net_recv_history

        data = resources.collect_with_rates()
        content = self.query_one("#resources-content", Static)

        if not data.get("available"):
            content.update(
                f"{status_indicator('error')} [bold red]Unavailable[/]\n"
                f"[dim]{data.get('error', 'psutil not installed')}[/]"
            )
            return

        lines = []

        # === CPU Section ===
        cpu = data.get("cpu", {})
        cpu_pct = cpu.get("percent", 0)

        # Track history
        _cpu_history.append(cpu_pct)
        if len(_cpu_history) > MAX_HISTORY:
            _cpu_history.pop(0)

        # CPU status color based on usage
        if cpu_pct > 90:
            cpu_status = "error"
        elif cpu_pct > 70:
            cpu_status = "warning"
        else:
            cpu_status = "ok"

        cpu_bar = progress_bar(cpu_pct / 100, width=12, show_percent=False, style="smooth")
        spark = sparkline(_cpu_history, width=10) if len(_cpu_history) > 1 else ""

        lines.append(
            f"{status_indicator(cpu_status)} [bold]CPU:[/] {cpu_pct:.1f}% {cpu_bar} {spark}"
        )

        # Per-core display (compact)
        per_core = cpu.get("per_core", [])
        if per_core:
            core_bars = []
            for i, pct in enumerate(per_core[:8]):  # Max 8 cores shown
                core_bars.append(mini_bar(pct / 100, width=2))
            lines.append(f"  Cores: {''.join(core_bars)} ({len(per_core)} total)")

        # Load average (if available)
        load = data.get("load")
        if load:
            lines.append(f"  Load: {load['1min']:.2f} / {load['5min']:.2f} / {load['15min']:.2f}")

        lines.append(separator(40, "dotted"))

        # === Memory Section ===
        mem = data.get("memory", {})
        mem_pct = mem.get("percent", 0)

        # Track history
        _mem_history.append(mem_pct)
        if len(_mem_history) > MAX_HISTORY:
            _mem_history.pop(0)

        # Memory status
        if mem_pct > 90:
            mem_status = "error"
        elif mem_pct > 75:
            mem_status = "warning"
        else:
            mem_status = "ok"

        mem_bar = progress_bar(mem_pct / 100, width=12, show_percent=False, style="smooth")
        spark = sparkline(_mem_history, width=10) if len(_mem_history) > 1 else ""

        lines.append(
            f"{status_indicator(mem_status)} [bold]MEM:[/] {mem_pct:.1f}% {mem_bar} {spark}"
        )
        lines.append(
            f"  {mem.get('used_gb', 0):.1f}G / {mem.get('total_gb', 0):.1f}G "
            f"({mem.get('available_gb', 0):.1f}G free)"
        )

        # Swap if significant
        swap_pct = mem.get("swap_percent", 0)
        if swap_pct > 5:
            swap_bar = mini_bar(swap_pct / 100, width=6)
            lines.append(f"  Swap: {swap_pct:.1f}% {swap_bar}")

        lines.append(separator(40, "dotted"))

        # === Disk Section ===
        disks = data.get("disks", [])
        if disks:
            lines.append(f"[bold]{STATUS_SYMBOLS['square_full']} DISK[/]")
            for disk in disks[:3]:  # Show max 3 disks
                pct = disk.get("percent", 0)
                if pct > 90:
                    disk_status = "error"
                elif pct > 75:
                    disk_status = "warning"
                else:
                    disk_status = "ok"

                disk_bar = mini_bar(pct / 100, width=8)
                mount = disk.get("mount", "?")
                if len(mount) > 12:
                    mount = "..." + mount[-9:]
                lines.append(
                    f"  {status_indicator(disk_status)} {mount}: {pct:.0f}% {disk_bar} "
                    f"({disk.get('free_gb', 0):.1f}G free)"
                )

        lines.append(separator(40, "dotted"))

        # === Network Section ===
        net = data.get("network", {})

        # Calculate rates if available
        rate_sent = net.get("rate_sent_bps")
        rate_recv = net.get("rate_recv_bps")

        # Track rate history for sparklines
        if rate_sent is not None:
            _net_sent_history.append(rate_sent / 1024)  # KB/s
            if len(_net_sent_history) > MAX_HISTORY:
                _net_sent_history.pop(0)

        if rate_recv is not None:
            _net_recv_history.append(rate_recv / 1024)  # KB/s
            if len(_net_recv_history) > MAX_HISTORY:
                _net_recv_history.pop(0)

        lines.append(f"[bold]{STATUS_SYMBOLS['lightning']} NET[/]")

        if rate_sent is not None and rate_recv is not None:
            sent_spark = sparkline(_net_sent_history, width=8) if len(_net_sent_history) > 1 else ""
            recv_spark = sparkline(_net_recv_history, width=8) if len(_net_recv_history) > 1 else ""

            lines.append(f"  {STATUS_SYMBOLS['arrow_up']} {_format_rate(rate_sent)} {sent_spark}")
            lines.append(f"  {STATUS_SYMBOLS['arrow_down']} {_format_rate(rate_recv)} {recv_spark}")
        else:
            # Fallback to totals
            lines.append(
                f"  {STATUS_SYMBOLS['arrow_up']} {_format_bytes(net.get('bytes_sent', 0))} total"
            )
            lines.append(
                f"  {STATUS_SYMBOLS['arrow_down']} {_format_bytes(net.get('bytes_recv', 0))} total"
            )

        content.update("\n".join(lines))


class CompactResourcesPanel(Static):
    """Compact single-line resources summary."""

    def compose(self) -> ComposeResult:
        yield Static("Loading...", id="resources-compact")

    def refresh_data(self) -> None:
        data = resources.collect()
        content = self.query_one("#resources-compact", Static)

        if not data.get("available"):
            content.update("[dim]Resources: unavailable[/]")
            return

        cpu = data.get("cpu", {}).get("percent", 0)
        mem = data.get("memory", {}).get("percent", 0)

        cpu_bar = mini_bar(cpu / 100, width=4)
        mem_bar = mini_bar(mem / 100, width=4)

        # Color based on status
        cpu_color = "red" if cpu > 90 else "yellow" if cpu > 70 else ""
        mem_color = "red" if mem > 90 else "yellow" if mem > 75 else ""

        cpu_str = f"[{cpu_color}]{cpu:.0f}%[/]" if cpu_color else f"{cpu:.0f}%"
        mem_str = f"[{mem_color}]{mem:.0f}%[/]" if mem_color else f"{mem:.0f}%"

        content.update(f"CPU: {cpu_str} {cpu_bar}  MEM: {mem_str} {mem_bar}")
