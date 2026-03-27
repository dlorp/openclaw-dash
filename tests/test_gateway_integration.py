"""Tests for gateway agent workflow integration."""

from __future__ import annotations

import httpx
import pytest

from openclaw_dash.services.gateway_client import GatewayClient, GatewayConfig, GatewayError


def make_client(handler) -> GatewayClient:
    """Create a GatewayClient backed by an httpx MockTransport."""
    client = GatewayClient(GatewayConfig(url="http://testserver", timeout=1.0))
    client._client.close()
    client._client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://testserver")
    return client


def test_spawn_agent_returns_session_key():
    """spawn_agent should return the session key from the gateway response."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/agents/spawn"
        assert request.read() == b'{"agent_id":"security-specialist","task":"Review PR 123"}'
        return httpx.Response(200, json={"session_key": "sess-123"})

    client = make_client(handler)

    try:
        session_key = client.spawn_agent("security-specialist", "Review PR 123")
    finally:
        client.close()

    assert session_key == "sess-123"


def test_get_session_status_returns_payload():
    """get_session_status should return the gateway JSON payload."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/sessions/sess-123"
        return httpx.Response(200, json={"state": "running", "completed": False})

    client = make_client(handler)

    try:
        status = client.get_session_status("sess-123")
    finally:
        client.close()

    assert status["session_key"] == "sess-123"
    assert status["state"] == "running"
    assert status["completed"] is False


def test_wait_for_agent_polls_until_completed(monkeypatch: pytest.MonkeyPatch):
    """wait_for_agent should poll until the session reaches completion."""
    statuses = iter(
        [
            {"state": "running", "completed": False},
            {"state": "completed", "completed": True, "result": "pass"},
        ]
    )

    client = GatewayClient(GatewayConfig(url="http://testserver", timeout=1.0))
    monkeypatch.setattr(client, "get_session_status", lambda session_key: next(statuses))
    monkeypatch.setattr("openclaw_dash.services.gateway_client.time.sleep", lambda _: None)

    status = client.wait_for_agent("sess-123", timeout=5)

    assert status["state"] == "completed"
    assert status["result"] == "pass"


def test_wait_for_agent_raises_on_terminal_failure(monkeypatch: pytest.MonkeyPatch):
    """wait_for_agent should surface failed terminal states."""
    client = GatewayClient(GatewayConfig(url="http://testserver", timeout=1.0))
    monkeypatch.setattr(
        client,
        "get_session_status",
        lambda session_key: {"state": "failed", "completed": True, "error": "review crashed"},
    )
    monkeypatch.setattr("openclaw_dash.services.gateway_client.time.sleep", lambda _: None)

    with pytest.raises(GatewayError, match="failed"):
        client.wait_for_agent("sess-123", timeout=5)

    client.close()


def test_wait_for_agent_times_out(monkeypatch: pytest.MonkeyPatch):
    """wait_for_agent should raise when the session never completes."""
    client = GatewayClient(GatewayConfig(url="http://testserver", timeout=1.0))
    monkeypatch.setattr(
        client,
        "get_session_status",
        lambda session_key: {"state": "running", "completed": False},
    )
    monkeypatch.setattr("openclaw_dash.services.gateway_client.time.sleep", lambda _: None)

    monotonic_values = iter([0.0, 0.1, 5.1])
    monkeypatch.setattr(
        "openclaw_dash.services.gateway_client.time.monotonic",
        lambda: next(monotonic_values),
    )

    with pytest.raises(GatewayError, match="Timed out"):
        client.wait_for_agent("sess-123", timeout=5)

    client.close()
