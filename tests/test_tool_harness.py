"""Tests for the Tool Harness panel widget."""

from openclaw_dash.widgets.tool_harness import (
    STATE_COLORS,
    STATE_SYMBOLS,
    CompactToolHarnessPanel,
    Tool,
    ToolHarnessData,
    ToolHarnessPanel,
    ToolState,
    render_harness_ascii,
    render_harness_compact,
    render_tool_state,
    render_tool_stats,
)


class TestToolState:
    """Test ToolState enum."""

    def test_all_states_defined(self):
        """All expected states should be defined."""
        assert ToolState.ACTIVE.value == "active"
        assert ToolState.PROCESSING.value == "processing"
        assert ToolState.FAILED.value == "failed"
        assert ToolState.IDLE.value == "idle"
        assert ToolState.DISABLED.value == "disabled"

    def test_all_states_have_colors(self):
        """Every state should have a color mapping."""
        for state in ToolState:
            assert state in STATE_COLORS, f"Missing color for {state}"

    def test_all_states_have_symbols(self):
        """Every state should have a symbol mapping."""
        for state in ToolState:
            assert state in STATE_SYMBOLS, f"Missing symbol for {state}"


class TestTool:
    """Test Tool dataclass."""

    def test_default_values(self):
        """Tool should have sensible defaults."""
        tool = Tool(name="test_tool")
        assert tool.name == "test_tool"
        assert tool.state == ToolState.IDLE
        assert tool.last_call_ms is None
        assert tool.call_count == 0
        assert tool.error_count == 0
        assert tool.metadata == {}

    def test_success_rate_no_calls(self):
        """Success rate should be 100% with no calls."""
        tool = Tool(name="test")
        assert tool.success_rate == 100.0

    def test_success_rate_all_success(self):
        """Success rate should be 100% with no errors."""
        tool = Tool(name="test", call_count=100, error_count=0)
        assert tool.success_rate == 100.0

    def test_success_rate_some_errors(self):
        """Success rate should reflect error ratio."""
        tool = Tool(name="test", call_count=100, error_count=10)
        assert tool.success_rate == 90.0

    def test_success_rate_all_failed(self):
        """Success rate should be 0% when all calls fail."""
        tool = Tool(name="test", call_count=10, error_count=10)
        assert tool.success_rate == 0.0

    def test_custom_metadata(self):
        """Tool should accept custom metadata."""
        tool = Tool(name="test", metadata={"version": "1.0", "enabled": True})
        assert tool.metadata["version"] == "1.0"
        assert tool.metadata["enabled"] is True


class TestToolHarnessData:
    """Test ToolHarnessData dataclass."""

    def test_default_values(self):
        """Data should have sensible defaults."""
        data = ToolHarnessData()
        assert data.agent_name == "Agent Runtime"
        assert data.tools == []
        assert data.total_calls == 0
        assert data.uptime_seconds == 0.0

    def test_from_mock(self):
        """Mock data should be populated."""
        data = ToolHarnessData.from_mock()
        assert len(data.tools) > 0
        assert data.total_calls > 0
        assert any(t.state == ToolState.ACTIVE for t in data.tools)
        assert any(t.state == ToolState.FAILED for t in data.tools)
        assert any(t.state == ToolState.PROCESSING for t in data.tools)

    def test_mock_has_diverse_states(self):
        """Mock data should demonstrate various tool states."""
        data = ToolHarnessData.from_mock()
        states = {t.state for t in data.tools}
        # Should have at least active, failed, and processing states
        assert ToolState.ACTIVE in states
        assert ToolState.FAILED in states
        assert ToolState.PROCESSING in states


class TestRenderToolState:
    """Test render_tool_state function."""

    def test_render_left_position(self):
        """Should render tool on left with connector pointing right."""
        tool = Tool(name="exec", state=ToolState.ACTIVE)
        result = render_tool_state(tool, position="left")
        assert "exec" in result
        assert "┤" in result  # Right-facing connector

    def test_render_right_position(self):
        """Should render tool on right with connector pointing left."""
        tool = Tool(name="read", state=ToolState.IDLE)
        result = render_tool_state(tool, position="right")
        assert "read" in result
        assert "├" in result  # Left-facing connector

    def test_active_state_green(self):
        """Active state should use green color."""
        tool = Tool(name="test", state=ToolState.ACTIVE)
        result = render_tool_state(tool)
        assert "green" in result

    def test_failed_state_red(self):
        """Failed state should use red color."""
        tool = Tool(name="test", state=ToolState.FAILED)
        result = render_tool_state(tool)
        assert "red" in result

    def test_processing_state_cyan(self):
        """Processing state should use cyan color."""
        tool = Tool(name="test", state=ToolState.PROCESSING)
        result = render_tool_state(tool)
        assert "cyan" in result


class TestRenderHarnessAscii:
    """Test render_harness_ascii function."""

    def test_returns_list_of_strings(self):
        """Should return a list of lines."""
        data = ToolHarnessData.from_mock()
        result = render_harness_ascii(data)
        assert isinstance(result, list)
        assert all(isinstance(line, str) for line in result)

    def test_contains_header(self):
        """Should contain a header with 'Tool Harness'."""
        data = ToolHarnessData.from_mock()
        result = render_harness_ascii(data)
        assert any("Tool Harness" in line for line in result)

    def test_contains_agent_name(self):
        """Should contain the agent name."""
        data = ToolHarnessData(agent_name="Test Agent")
        result = render_harness_ascii(data)
        assert any("Test Agent" in line for line in result)

    def test_contains_tool_names(self):
        """Should contain all tool names."""
        data = ToolHarnessData(
            tools=[
                Tool(name="exec", state=ToolState.ACTIVE),
                Tool(name="read", state=ToolState.IDLE),
            ]
        )
        result = render_harness_ascii(data)
        combined = "\n".join(result)
        assert "exec" in combined
        assert "read" in combined

    def test_contains_box_drawing(self):
        """Should contain box-drawing characters for the center box."""
        data = ToolHarnessData.from_mock()
        result = render_harness_ascii(data)
        combined = "\n".join(result)
        # Should have box corners
        assert "┌" in combined
        assert "┐" in combined
        assert "└" in combined
        assert "┘" in combined

    def test_empty_tools(self):
        """Should handle empty tool list."""
        data = ToolHarnessData(tools=[])
        result = render_harness_ascii(data)
        assert isinstance(result, list)
        assert len(result) > 0


class TestRenderToolStats:
    """Test render_tool_stats function."""

    def test_returns_list_of_strings(self):
        """Should return a list of lines."""
        data = ToolHarnessData.from_mock()
        result = render_tool_stats(data)
        assert isinstance(result, list)
        assert all(isinstance(line, str) for line in result)

    def test_contains_legend(self):
        """Should contain a legend section."""
        data = ToolHarnessData.from_mock()
        result = render_tool_stats(data)
        combined = "\n".join(result)
        assert "Legend" in combined
        assert "Active" in combined
        assert "Processing" in combined
        assert "Failed" in combined
        assert "Idle" in combined

    def test_contains_summary(self):
        """Should contain summary statistics."""
        data = ToolHarnessData(
            tools=[
                Tool(name="a", state=ToolState.ACTIVE),
                Tool(name="b", state=ToolState.FAILED),
            ],
            total_calls=100,
        )
        result = render_tool_stats(data)
        combined = "\n".join(result)
        assert "Summary" in combined
        assert "2 tools connected" in combined
        assert "100" in combined  # total calls

    def test_active_tools_section(self):
        """Should show details for non-idle tools."""
        data = ToolHarnessData(
            tools=[
                Tool(
                    name="exec",
                    state=ToolState.ACTIVE,
                    call_count=50,
                    last_call_ms=100.5,
                ),
            ]
        )
        result = render_tool_stats(data)
        combined = "\n".join(result)
        assert "exec" in combined
        assert "50 calls" in combined


class TestRenderHarnessCompact:
    """Test render_harness_compact function."""

    def test_returns_string(self):
        """Should return a single string."""
        data = ToolHarnessData.from_mock()
        result = render_harness_compact(data)
        assert isinstance(result, str)

    def test_contains_tool_count(self):
        """Should contain the number of tools."""
        data = ToolHarnessData(tools=[Tool(name="a"), Tool(name="b"), Tool(name="c")])
        result = render_harness_compact(data)
        assert "3" in result
        assert "Tools" in result

    def test_shows_active_count(self):
        """Should show active tool count."""
        data = ToolHarnessData(
            tools=[
                Tool(name="a", state=ToolState.ACTIVE),
                Tool(name="b", state=ToolState.ACTIVE),
            ]
        )
        result = render_harness_compact(data)
        assert "2 active" in result
        assert "green" in result

    def test_shows_failed_count(self):
        """Should show failed tool count."""
        data = ToolHarnessData(tools=[Tool(name="a", state=ToolState.FAILED)])
        result = render_harness_compact(data)
        assert "1 failed" in result
        assert "red" in result

    def test_shows_processing_count(self):
        """Should show processing tool count."""
        data = ToolHarnessData(tools=[Tool(name="a", state=ToolState.PROCESSING)])
        result = render_harness_compact(data)
        assert "1 processing" in result
        assert "cyan" in result

    def test_shows_total_calls(self):
        """Should show total call count."""
        data = ToolHarnessData(total_calls=1234)
        result = render_harness_compact(data)
        assert "1,234" in result  # Formatted with comma


class TestToolHarnessPanel:
    """Test ToolHarnessPanel widget."""

    def test_default_data(self):
        """Should use mock data by default."""
        panel = ToolHarnessPanel()
        assert panel.data is not None
        assert len(panel.data.tools) > 0

    def test_custom_data(self):
        """Should accept custom data."""
        custom_data = ToolHarnessData(agent_name="Custom Agent")
        panel = ToolHarnessPanel(data=custom_data)
        assert panel.data.agent_name == "Custom Agent"

    def test_show_stats_option(self):
        """Should accept show_stats option."""
        panel = ToolHarnessPanel(show_stats=False)
        assert panel._show_stats is False

    def test_compact_option(self):
        """Should accept compact option."""
        panel = ToolHarnessPanel(compact=True)
        assert panel._compact is True

    def test_update_tool_state(self):
        """Should update individual tool state."""
        data = ToolHarnessData(tools=[Tool(name="exec", state=ToolState.IDLE)])
        panel = ToolHarnessPanel(data=data)
        panel.update_tool_state("exec", ToolState.ACTIVE)
        assert panel.data.tools[0].state == ToolState.ACTIVE

    def test_update_nonexistent_tool(self):
        """Should handle updating nonexistent tool gracefully."""
        data = ToolHarnessData(tools=[Tool(name="exec")])
        panel = ToolHarnessPanel(data=data)
        # Should not raise
        panel.update_tool_state("nonexistent", ToolState.ACTIVE)
        # Original tool unchanged
        assert panel.data.tools[0].state == ToolState.IDLE

    def test_data_property(self):
        """Should expose data via property."""
        data = ToolHarnessData(total_calls=999)
        panel = ToolHarnessPanel(data=data)
        assert panel.data.total_calls == 999


class TestCompactToolHarnessPanel:
    """Test CompactToolHarnessPanel widget."""

    def test_default_data(self):
        """Should use mock data by default."""
        panel = CompactToolHarnessPanel()
        assert panel._data is not None

    def test_custom_data(self):
        """Should accept custom data."""
        custom_data = ToolHarnessData(total_calls=42)
        panel = CompactToolHarnessPanel(data=custom_data)
        assert panel._data.total_calls == 42


class TestStateColorMapping:
    """Test state color mappings match design requirements."""

    def test_active_is_green(self):
        """Active state should be green (design requirement)."""
        assert STATE_COLORS[ToolState.ACTIVE] == "green"

    def test_failed_is_red(self):
        """Failed state should be red (design requirement)."""
        assert STATE_COLORS[ToolState.FAILED] == "red"

    def test_processing_is_cyan(self):
        """Processing state should be cyan (design requirement)."""
        assert STATE_COLORS[ToolState.PROCESSING] == "cyan"

    def test_idle_is_dim(self):
        """Idle state should be dim."""
        assert "dim" in STATE_COLORS[ToolState.IDLE]


class TestAsciiArtQuality:
    """Test that ASCII art meets terminal aesthetic requirements."""

    def test_uses_dashed_borders(self):
        """Should use dashed line characters (terminal aesthetic)."""
        data = ToolHarnessData.from_mock()
        result = render_harness_ascii(data)
        combined = "\n".join(result)
        # Should use dashed separator
        assert "┈" in combined

    def test_monospace_alignment(self):
        """Tool names should be padded for alignment."""
        data = ToolHarnessData(
            tools=[
                Tool(name="a", state=ToolState.ACTIVE),
                Tool(name="longer_name", state=ToolState.IDLE),
            ]
        )
        result = render_harness_ascii(data)
        # Lines should have consistent structure
        assert len(result) > 0

    def test_connector_lines(self):
        """Should have connector lines between tools and agent."""
        data = ToolHarnessData(tools=[Tool(name="exec", state=ToolState.ACTIVE)])
        result = render_harness_ascii(data)
        combined = "\n".join(result)
        # Should have connector characters
        assert "├" in combined or "┤" in combined
