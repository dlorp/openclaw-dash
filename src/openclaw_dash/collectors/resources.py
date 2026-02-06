"""System resource collector using psutil."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from openclaw_dash.demo import is_demo_mode

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


def _mock_resources() -> dict[str, Any]:
    """Return mock resource data for demo mode."""
    return {
        "available": True,
        "cpu": {
            "percent": 23.5,
            "per_core": [18.2, 25.1, 22.8, 27.9],
            "cores_logical": 4,
            "cores_physical": 2,
            "freq_current": 2400.0,
            "freq_max": 3200.0,
        },
        "memory": {
            "total": 17179869184,
            "available": 8589934592,
            "used": 8589934592,
            "percent": 50.0,
            "total_gb": 16.0,
            "used_gb": 8.0,
            "available_gb": 8.0,
            "swap_total": 4294967296,
            "swap_used": 536870912,
            "swap_percent": 12.5,
        },
        "disks": [
            {
                "mount": "/",
                "device": "/dev/disk1s1",
                "fstype": "apfs",
                "total": 499963174912,
                "used": 299977904947,
                "free": 199985269965,
                "percent": 60.0,
                "total_gb": 465.6,
                "used_gb": 279.4,
                "free_gb": 186.2,
            }
        ],
        "network": {
            "bytes_sent": 1073741824,
            "bytes_recv": 5368709120,
            "packets_sent": 1000000,
            "packets_recv": 5000000,
            "bytes_sent_mb": 1024.0,
            "bytes_recv_mb": 5120.0,
            "interfaces": [
                {
                    "name": "en0",
                    "bytes_sent": 1073741824,
                    "bytes_recv": 5368709120,
                    "sent_mb": 1024.0,
                    "recv_mb": 5120.0,
                }
            ],
        },
        "load": {"1min": 1.25, "5min": 1.50, "15min": 1.35},
        "collected_at": datetime.now().isoformat(),
    }


def collect() -> dict[str, Any]:
    """Collect system resource metrics.

    Returns:
        Dictionary containing CPU, memory, disk, and network metrics.
    """
    # Return mock data in demo mode
    if is_demo_mode():
        return _mock_resources()

    if not PSUTIL_AVAILABLE:
        return {
            "available": False,
            "error": "psutil not installed",
            "collected_at": datetime.now().isoformat(),
        }

    try:
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
        cpu_count_logical = psutil.cpu_count(logical=True)
        cpu_count_physical = psutil.cpu_count(logical=False)
        cpu_freq = psutil.cpu_freq()

        cpu = {
            "percent": cpu_percent,
            "per_core": cpu_per_core,
            "cores_logical": cpu_count_logical,
            "cores_physical": cpu_count_physical,
            "freq_current": cpu_freq.current if cpu_freq else None,
            "freq_max": cpu_freq.max if cpu_freq else None,
        }

        # Memory metrics
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        memory = {
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
            "percent": mem.percent,
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "swap_total": swap.total,
            "swap_used": swap.used,
            "swap_percent": swap.percent,
        }

        # Disk metrics - key mounts only
        disk_partitions = psutil.disk_partitions()
        disks = []
        key_mounts = {"/", "/home", "/Users", "/var", "/tmp", "/opt"}

        for partition in disk_partitions:
            # Skip special filesystems
            if partition.fstype in ("devfs", "tmpfs", "squashfs", "overlay"):
                continue
            # Only include key mounts or root-like mounts
            if partition.mountpoint in key_mounts or partition.mountpoint.startswith(
                ("/Volumes", "/mnt", "/media")
            ):
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disks.append(
                        {
                            "mount": partition.mountpoint,
                            "device": partition.device,
                            "fstype": partition.fstype,
                            "total": usage.total,
                            "used": usage.used,
                            "free": usage.free,
                            "percent": usage.percent,
                            "total_gb": round(usage.total / (1024**3), 2),
                            "used_gb": round(usage.used / (1024**3), 2),
                            "free_gb": round(usage.free / (1024**3), 2),
                        }
                    )
                except (PermissionError, OSError):
                    continue

        # Also always include root if not already
        if not any(d["mount"] == "/" for d in disks):
            try:
                usage = psutil.disk_usage("/")
                disks.insert(
                    0,
                    {
                        "mount": "/",
                        "device": "root",
                        "fstype": "unknown",
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent,
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2),
                    },
                )
            except (PermissionError, OSError):
                pass

        # Network I/O
        net_io = psutil.net_io_counters()
        network = {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
            "bytes_sent_mb": round(net_io.bytes_sent / (1024**2), 2),
            "bytes_recv_mb": round(net_io.bytes_recv / (1024**2), 2),
        }

        # Per-interface stats (top 3 active)
        try:
            net_per_if = psutil.net_io_counters(pernic=True)
            interfaces = []
            for name, stats in sorted(
                net_per_if.items(), key=lambda x: x[1].bytes_sent + x[1].bytes_recv, reverse=True
            )[:3]:
                if name.startswith(("lo", "docker", "veth", "br-")):
                    continue
                interfaces.append(
                    {
                        "name": name,
                        "bytes_sent": stats.bytes_sent,
                        "bytes_recv": stats.bytes_recv,
                        "sent_mb": round(stats.bytes_sent / (1024**2), 2),
                        "recv_mb": round(stats.bytes_recv / (1024**2), 2),
                    }
                )
            network["interfaces"] = interfaces
        except Exception:
            network["interfaces"] = []

        # Load average (Unix only)
        try:
            load_avg = psutil.getloadavg()
            load = {
                "1min": round(load_avg[0], 2),
                "5min": round(load_avg[1], 2),
                "15min": round(load_avg[2], 2),
            }
        except (AttributeError, OSError):
            load = None

        return {
            "available": True,
            "cpu": cpu,
            "memory": memory,
            "disks": disks,
            "network": network,
            "load": load,
            "collected_at": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "available": False,
            "error": str(e),
            "collected_at": datetime.now().isoformat(),
        }


# Cache for calculating rates
_last_network: dict[str, int] | None = None
_last_network_time: float | None = None


def collect_with_rates() -> dict[str, Any]:
    """Collect system resources including network I/O rates.

    Calculates bytes/second rates by comparing to previous collection.
    """
    # Return mock data in demo mode (with mock rates)
    if is_demo_mode():
        data = _mock_resources()
        data["network"]["rate_sent_bps"] = 51200.0  # 50 KB/s
        data["network"]["rate_recv_bps"] = 256000.0  # 250 KB/s
        data["network"]["rate_sent_kbps"] = 50.0
        data["network"]["rate_recv_kbps"] = 250.0
        return data

    global _last_network, _last_network_time

    import time

    data = collect()
    if not data.get("available"):
        return data

    current_time = time.time()
    current_network = {
        "bytes_sent": data["network"]["bytes_sent"],
        "bytes_recv": data["network"]["bytes_recv"],
    }

    # Calculate rates if we have previous data
    if _last_network is not None and _last_network_time is not None:
        elapsed = current_time - _last_network_time
        if elapsed > 0:
            sent_rate = (current_network["bytes_sent"] - _last_network["bytes_sent"]) / elapsed
            recv_rate = (current_network["bytes_recv"] - _last_network["bytes_recv"]) / elapsed

            data["network"]["rate_sent_bps"] = max(0, sent_rate)
            data["network"]["rate_recv_bps"] = max(0, recv_rate)
            data["network"]["rate_sent_kbps"] = round(max(0, sent_rate) / 1024, 2)
            data["network"]["rate_recv_kbps"] = round(max(0, recv_rate) / 1024, 2)

    _last_network = current_network
    _last_network_time = current_time

    return data
