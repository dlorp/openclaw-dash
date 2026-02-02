"""Tests for openclaw CLI parser."""

from openclaw_dash.collectors.openclaw_cli import (
    parse_heartbeat,
    parse_latency,
    parse_session_count,
    parse_status_output,
    parse_tokens,
    status_to_gateway_data,
    status_to_sessions_data,
)

SAMPLE_STATUS_OUTPUT = """OpenClaw status

Overview
┌─────────────────┬───────────────────────────────────────┐
│ Item            │ Value                                 │
├─────────────────┼───────────────────────────────────────┤
│ OS              │ macos 15.6.1 (x64) · node 22.22.0     │
│ Gateway         │ local · ws://127.0.0.1:18789 · reachable 20ms │
│ Gateway service │ LaunchAgent installed · not loaded    │
│ Agents          │ 1 · no bootstraps · sessions 51       │
│ Memory          │ enabled (plugin memory-core) · unavailable │
│ Heartbeat       │ 30m (main)                            │
│ Sessions        │ 51 active · default claude-opus-4-5 (200k ctx) │
└─────────────────┴───────────────────────────────────────┘

Channels
┌──────────┬─────────┬────────┬────────────────────────────┐
│ Channel  │ Enabled │ State  │ Detail                     │
├──────────┼─────────┼────────┼────────────────────────────┤
│ Discord  │ ON      │ OK     │ token config               │
└──────────┴─────────┴────────┴────────────────────────────┘

Sessions
┌──────────────────────────────┬────────┬──────────┬─────────────────┬─────────────────┐
│ Key                          │ Kind   │ Age      │ Model           │ Tokens          │
├──────────────────────────────┼────────┼──────────┼─────────────────┼─────────────────┤
│ agent:main:discord:channel   │ group  │ just now │ claude-opus-4-5 │ 95k/200k (48%)  │
│ agent:main:main              │ direct │ 6m ago   │ claude-opus-4-5 │ 163k/200k (82%) │
│ agent:main:subagent:test     │ direct │ 18m ago  │ claude-opus-4-5 │ 51k/200k (26%)  │
└──────────────────────────────┴────────┴──────────┴─────────────────┴─────────────────┘

Update available (npm 2026.1.30). Run: openclaw update
"""


class TestParseLatency:
    def test_parses_ms(self):
        assert parse_latency("reachable 20ms") == 20

    def test_parses_larger_values(self):
        assert parse_latency("reachable 150ms · auth token") == 150

    def test_returns_none_when_not_found(self):
        assert parse_latency("unreachable") is None


class TestParseTokens:
    def test_parses_standard_format(self):
        used, total, pct = parse_tokens("95k/200k (48%)")
        assert used == 95000
        assert total == 200000
        assert pct == 48.0

    def test_parses_decimal_format(self):
        used, total, pct = parse_tokens("0.0k/200k (0%)")
        assert used == 0
        assert total == 200000
        assert pct == 0.0

    def test_parses_high_usage(self):
        used, total, pct = parse_tokens("163k/200k (82%)")
        assert used == 163000
        assert total == 200000
        assert pct == 82.0


class TestParseSessionCount:
    def test_parses_count(self):
        assert parse_session_count("sessions 51") == 51

    def test_parses_with_prefix(self):
        assert parse_session_count("1 · no bootstraps · sessions 51 · default main") == 51


class TestParseHeartbeat:
    def test_parses_minutes(self):
        assert parse_heartbeat("30m (main)") == "30m"

    def test_parses_hours(self):
        assert parse_heartbeat("1h") == "1h"


class TestParseStatusOutput:
    def test_parses_gateway_info(self):
        status = parse_status_output(SAMPLE_STATUS_OUTPUT)
        assert status.gateway_mode == "local"
        assert status.gateway_reachable is True
        assert status.gateway_latency_ms == 20

    def test_parses_memory_info(self):
        status = parse_status_output(SAMPLE_STATUS_OUTPUT)
        assert status.memory_enabled is True
        assert status.memory_status == "unavailable"

    def test_parses_heartbeat(self):
        status = parse_status_output(SAMPLE_STATUS_OUTPUT)
        assert status.heartbeat_interval == "30m"

    def test_parses_session_count(self):
        status = parse_status_output(SAMPLE_STATUS_OUTPUT)
        assert status.session_count == 51

    def test_parses_default_model(self):
        status = parse_status_output(SAMPLE_STATUS_OUTPUT)
        assert status.default_model == "claude-opus-4-5"
        assert status.default_context == 200000

    def test_parses_channels(self):
        status = parse_status_output(SAMPLE_STATUS_OUTPUT)
        assert len(status.channels) == 1
        assert status.channels[0]["name"] == "Discord"
        assert status.channels[0]["enabled"] is True

    def test_parses_sessions_table(self):
        status = parse_status_output(SAMPLE_STATUS_OUTPUT)
        assert len(status.sessions) == 3
        session = status.sessions[0]
        assert session.kind == "group"
        assert session.model == "claude-opus-4-5"
        assert session.tokens_used == 95000

    def test_detects_update_available(self):
        status = parse_status_output(SAMPLE_STATUS_OUTPUT)
        assert status.update_available is True


class TestStatusToGatewayData:
    def test_converts_to_gateway_format(self):
        status = parse_status_output(SAMPLE_STATUS_OUTPUT)
        data = status_to_gateway_data(status)
        assert data["healthy"] is True
        assert data["mode"] == "local"
        assert data["latency_ms"] == 20
        assert data["memory_enabled"] is True
        assert data["heartbeat_interval"] == "30m"
        assert "collected_at" in data


class TestStatusToSessionsData:
    def test_converts_to_sessions_format(self):
        status = parse_status_output(SAMPLE_STATUS_OUTPUT)
        data = status_to_sessions_data(status)
        assert data["total"] == 3
        assert data["active"] == 3
        assert data["default_model"] == "claude-opus-4-5"
        assert len(data["sessions"]) == 3


class TestEmptyOutput:
    def test_handles_empty_string(self):
        status = parse_status_output("")
        assert status.gateway_reachable is False
        assert status.session_count == 0
        assert len(status.sessions) == 0
