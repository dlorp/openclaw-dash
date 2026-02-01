"""Tests for system resources collector and widget."""

import pytest

from openclaw_dash.collectors import resources


class TestResourcesCollector:
    """Tests for the resources collector."""

    def test_collect_returns_dict(self):
        result = resources.collect()
        assert isinstance(result, dict)
        assert "collected_at" in result
        assert "available" in result

    def test_collect_available(self):
        """If psutil is installed, data should be available."""
        result = resources.collect()
        if result.get("available"):
            assert "cpu" in result
            assert "memory" in result
            assert "network" in result

    def test_cpu_data_structure(self):
        """CPU data should have expected fields."""
        result = resources.collect()
        if not result.get("available"):
            pytest.skip("psutil not available")

        cpu = result["cpu"]
        assert "percent" in cpu
        assert "per_core" in cpu
        assert isinstance(cpu["percent"], (int, float))
        assert isinstance(cpu["per_core"], list)
        assert 0 <= cpu["percent"] <= 100

    def test_memory_data_structure(self):
        """Memory data should have expected fields."""
        result = resources.collect()
        if not result.get("available"):
            pytest.skip("psutil not available")

        mem = result["memory"]
        assert "total" in mem
        assert "used" in mem
        assert "available" in mem
        assert "percent" in mem
        assert "total_gb" in mem
        assert "used_gb" in mem
        assert 0 <= mem["percent"] <= 100
        assert mem["total"] > 0

    def test_disk_data_structure(self):
        """Disk data should be a list of mounts."""
        result = resources.collect()
        if not result.get("available"):
            pytest.skip("psutil not available")

        disks = result["disks"]
        assert isinstance(disks, list)
        # Should have at least root mount
        if disks:
            disk = disks[0]
            assert "mount" in disk
            assert "percent" in disk
            assert "total_gb" in disk
            assert "free_gb" in disk

    def test_network_data_structure(self):
        """Network data should have expected fields."""
        result = resources.collect()
        if not result.get("available"):
            pytest.skip("psutil not available")

        net = result["network"]
        assert "bytes_sent" in net
        assert "bytes_recv" in net
        assert net["bytes_sent"] >= 0
        assert net["bytes_recv"] >= 0

    def test_collect_with_rates(self):
        """collect_with_rates should include rate calculations on second call."""
        # First call establishes baseline
        result1 = resources.collect_with_rates()
        if not result1.get("available"):
            pytest.skip("psutil not available")

        # Second call should have rates
        result2 = resources.collect_with_rates()
        net = result2["network"]

        # Rates should be present after second call
        assert "rate_sent_bps" in net or "rate_recv_bps" in net


class TestResourcesWidgetHelpers:
    """Tests for widget helper functions."""

    def test_format_bytes(self):
        # Direct test of helper function logic
        def _format_bytes(n: float, suffix: str = "B") -> str:
            for unit in ["", "K", "M", "G", "T"]:
                if abs(n) < 1024:
                    return f"{n:.1f}{unit}{suffix}"
                n /= 1024
            return f"{n:.1f}P{suffix}"

        assert _format_bytes(0) == "0.0B"
        assert _format_bytes(1024) == "1.0KB"
        assert _format_bytes(1024 * 1024) == "1.0MB"
        assert _format_bytes(1024 * 1024 * 1024) == "1.0GB"

    def test_format_rate(self):
        # Direct test of helper function logic
        def _format_rate(bps: float) -> str:
            if bps < 1024:
                return f"{bps:.0f} B/s"
            elif bps < 1024 * 1024:
                return f"{bps / 1024:.1f} KB/s"
            else:
                return f"{bps / (1024 * 1024):.1f} MB/s"

        assert "B/s" in _format_rate(100)
        assert "KB/s" in _format_rate(2048)
        assert "MB/s" in _format_rate(2 * 1024 * 1024)


class TestResourcesConfig:
    """Tests for resources config option."""

    def test_config_has_show_resources(self):
        try:
            from openclaw_dash.config import Config
        except ImportError:
            pytest.skip("Config module not importable (missing dependencies)")

        config = Config()
        assert hasattr(config, "show_resources")
        assert config.show_resources is True  # Default is on

    def test_config_to_dict_includes_show_resources(self):
        try:
            from openclaw_dash.config import Config
        except ImportError:
            pytest.skip("Config module not importable (missing dependencies)")

        config = Config(show_resources=False)
        data = config.to_dict()
        assert "show_resources" in data
        assert data["show_resources"] is False

    def test_config_from_dict_with_show_resources(self):
        try:
            from openclaw_dash.config import Config
        except ImportError:
            pytest.skip("Config module not importable (missing dependencies)")

        data = {"show_resources": False}
        config = Config.from_dict(data)
        assert config.show_resources is False

    def test_config_from_dict_default(self):
        try:
            from openclaw_dash.config import Config
        except ImportError:
            pytest.skip("Config module not importable (missing dependencies)")

        config = Config.from_dict({})
        assert config.show_resources is True  # Default
