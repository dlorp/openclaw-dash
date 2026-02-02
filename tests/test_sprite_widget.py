"""Tests for the tamagotchi-style sprite widget."""

from openclaw_dash.widgets.sprite import (
    DEFAULT_STATUS_TEXT,
    SPRITE_FRAMES,
    STATE_COLORS,
    STATE_ICONS,
    CompactSpriteWidget,
    SpriteState,
    SpriteWidget,
    create_sprite,
    format_sprite_status,
    get_sprite_frame,
    get_state_color,
    get_state_icon,
    parse_state,
)


class TestSpriteState:
    """Tests for SpriteState enum."""

    def test_sprite_state_values(self):
        """Test that all sprite state values are correct."""
        assert SpriteState.IDLE.value == "idle"
        assert SpriteState.THINKING.value == "thinking"
        assert SpriteState.WORKING.value == "working"
        assert SpriteState.SPAWNING.value == "spawning"
        assert SpriteState.DONE.value == "done"
        assert SpriteState.ALERT.value == "alert"

    def test_all_states_defined(self):
        """Test all expected states exist."""
        states = list(SpriteState)
        assert len(states) == 6


class TestParseState:
    """Tests for parse_state function."""

    def test_parse_valid_string(self):
        """Test parsing valid state strings."""
        assert parse_state("idle") == SpriteState.IDLE
        assert parse_state("thinking") == SpriteState.THINKING
        assert parse_state("working") == SpriteState.WORKING
        assert parse_state("spawning") == SpriteState.SPAWNING
        assert parse_state("done") == SpriteState.DONE
        assert parse_state("alert") == SpriteState.ALERT

    def test_parse_case_insensitive(self):
        """Test parsing is case insensitive."""
        assert parse_state("IDLE") == SpriteState.IDLE
        assert parse_state("Thinking") == SpriteState.THINKING
        assert parse_state("WORKING") == SpriteState.WORKING

    def test_parse_enum_passthrough(self):
        """Test passing SpriteState enum returns same value."""
        assert parse_state(SpriteState.IDLE) == SpriteState.IDLE
        assert parse_state(SpriteState.ALERT) == SpriteState.ALERT

    def test_parse_invalid_returns_idle(self):
        """Test invalid input returns IDLE state."""
        assert parse_state("invalid") == SpriteState.IDLE
        assert parse_state("unknown") == SpriteState.IDLE
        assert parse_state("") == SpriteState.IDLE

    def test_parse_none_returns_idle(self):
        """Test None returns IDLE state."""
        assert parse_state(None) == SpriteState.IDLE


class TestSpriteFrames:
    """Tests for sprite ASCII art frames."""

    def test_all_states_have_frames(self):
        """Test all states have animation frames defined."""
        for state in SpriteState:
            assert state in SPRITE_FRAMES
            assert len(SPRITE_FRAMES[state]) >= 1

    def test_all_states_have_two_frames(self):
        """Test all states have exactly 2 frames for animation."""
        for state in SpriteState:
            assert len(SPRITE_FRAMES[state]) == 2

    def test_frames_are_non_empty(self):
        """Test all frames contain content."""
        for state in SpriteState:
            for frame in SPRITE_FRAMES[state]:
                assert len(frame) > 0
                assert frame.strip() != ""

    def test_get_sprite_frame_valid(self):
        """Test getting valid sprite frames."""
        frame0 = get_sprite_frame(SpriteState.IDLE, 0)
        frame1 = get_sprite_frame(SpriteState.IDLE, 1)
        assert frame0 != ""
        assert frame1 != ""
        # Frames should be different for animation
        assert frame0 != frame1

    def test_get_sprite_frame_wraps(self):
        """Test frame index wraps around."""
        frame0 = get_sprite_frame(SpriteState.IDLE, 0)
        frame2 = get_sprite_frame(SpriteState.IDLE, 2)
        assert frame0 == frame2  # Frame 2 should wrap to frame 0

    def test_get_sprite_frame_negative(self):
        """Test negative frame index is handled."""
        # Python's modulo handles negatives
        frame = get_sprite_frame(SpriteState.IDLE, -1)
        assert frame != ""


class TestStateIcons:
    """Tests for state icons."""

    def test_all_states_have_icons(self):
        """Test all states have icons defined."""
        for state in SpriteState:
            assert state in STATE_ICONS

    def test_get_state_icon(self):
        """Test getting state icons."""
        assert get_state_icon(SpriteState.IDLE) == "😴"
        assert get_state_icon(SpriteState.THINKING) == "🤔"
        assert get_state_icon(SpriteState.WORKING) == "⚡"
        assert get_state_icon(SpriteState.SPAWNING) == "👥"
        assert get_state_icon(SpriteState.DONE) == "✅"
        assert get_state_icon(SpriteState.ALERT) == "⚠️"


class TestStateColors:
    """Tests for state colors."""

    def test_all_states_have_colors(self):
        """Test all states have colors defined."""
        for state in SpriteState:
            assert state in STATE_COLORS

    def test_get_state_color(self):
        """Test getting state colors."""
        assert get_state_color(SpriteState.IDLE) == "dim"
        assert get_state_color(SpriteState.THINKING) == "yellow"
        assert get_state_color(SpriteState.WORKING) == "cyan"
        assert get_state_color(SpriteState.SPAWNING) == "magenta"
        assert get_state_color(SpriteState.DONE) == "green"
        assert get_state_color(SpriteState.ALERT) == "red"


class TestDefaultStatusText:
    """Tests for default status text."""

    def test_all_states_have_default_text(self):
        """Test all states have default status text."""
        for state in SpriteState:
            assert state in DEFAULT_STATUS_TEXT

    def test_default_text_values(self):
        """Test default status text values."""
        assert DEFAULT_STATUS_TEXT[SpriteState.IDLE] == "zzz..."
        assert DEFAULT_STATUS_TEXT[SpriteState.THINKING] == "hmm..."
        assert DEFAULT_STATUS_TEXT[SpriteState.WORKING] == "working..."
        assert DEFAULT_STATUS_TEXT[SpriteState.SPAWNING] == "spawning..."
        assert DEFAULT_STATUS_TEXT[SpriteState.DONE] == "done!"
        assert DEFAULT_STATUS_TEXT[SpriteState.ALERT] == "attention!"


class TestSpriteWidget:
    """Tests for the SpriteWidget class."""

    def test_widget_creation(self):
        """Test basic widget creation."""
        widget = SpriteWidget()
        assert widget is not None
        assert widget.state == SpriteState.IDLE
        assert widget._compact is False

    def test_widget_with_state(self):
        """Test widget creation with initial state."""
        widget = SpriteWidget(state=SpriteState.WORKING)
        assert widget.state == SpriteState.WORKING

    def test_widget_with_string_state(self):
        """Test widget creation with string state."""
        widget = SpriteWidget(state="thinking")
        assert widget.state == SpriteState.THINKING

    def test_widget_with_status_text(self):
        """Test widget creation with custom status text."""
        widget = SpriteWidget(status_text="doing stuff...")
        assert widget.status_text == "doing stuff..."

    def test_widget_default_status_text(self):
        """Test widget uses default status text."""
        widget = SpriteWidget(state=SpriteState.SPAWNING)
        assert widget.status_text == "spawning..."

    def test_widget_compact_mode(self):
        """Test widget compact mode."""
        widget = SpriteWidget(compact=True)
        assert widget._compact is True

    def test_set_state(self):
        """Test set_state method."""
        widget = SpriteWidget()
        widget.set_state(SpriteState.ALERT)
        assert widget.state == SpriteState.ALERT

    def test_set_state_with_text(self):
        """Test set_state with custom status text."""
        widget = SpriteWidget()
        widget.set_state(SpriteState.WORKING, status_text="compiling...")
        assert widget.state == SpriteState.WORKING
        assert widget.status_text == "compiling..."

    def test_set_state_string(self):
        """Test set_state with string state."""
        widget = SpriteWidget()
        widget.set_state("done")
        assert widget.state == SpriteState.DONE

    def test_advance_frame(self):
        """Test frame advancement."""
        widget = SpriteWidget()
        assert widget.frame == 0
        widget.advance_frame()
        assert widget.frame == 1
        widget.advance_frame()
        assert widget.frame == 0  # Wraps around

    def test_animate(self):
        """Test animate method (alias for advance_frame)."""
        widget = SpriteWidget()
        assert widget.frame == 0
        widget.animate()
        assert widget.frame == 1

    def test_initial_frame(self):
        """Test initial frame is 0."""
        widget = SpriteWidget()
        assert widget.frame == 0


class TestCompactSpriteWidget:
    """Tests for the CompactSpriteWidget class."""

    def test_compact_widget_creation(self):
        """Test compact widget creation."""
        widget = CompactSpriteWidget()
        assert widget is not None
        assert widget._compact is True

    def test_compact_widget_with_state(self):
        """Test compact widget with initial state."""
        widget = CompactSpriteWidget(state=SpriteState.ALERT)
        assert widget.state == SpriteState.ALERT

    def test_compact_widget_with_string_state(self):
        """Test compact widget with string state."""
        widget = CompactSpriteWidget(state="spawning")
        assert widget.state == SpriteState.SPAWNING

    def test_compact_widget_inherits_methods(self):
        """Test compact widget inherits parent methods."""
        widget = CompactSpriteWidget()
        widget.set_state(SpriteState.DONE)
        assert widget.state == SpriteState.DONE
        widget.advance_frame()
        assert widget.frame == 1


class TestCreateSprite:
    """Tests for the create_sprite factory function."""

    def test_create_sprite_default(self):
        """Test creating sprite with defaults."""
        sprite = create_sprite()
        assert isinstance(sprite, SpriteWidget)
        assert sprite.state == SpriteState.IDLE

    def test_create_sprite_with_state(self):
        """Test creating sprite with state."""
        sprite = create_sprite(state=SpriteState.THINKING)
        assert sprite.state == SpriteState.THINKING

    def test_create_sprite_compact(self):
        """Test creating compact sprite."""
        sprite = create_sprite(compact=True)
        assert isinstance(sprite, CompactSpriteWidget)

    def test_create_sprite_with_text(self):
        """Test creating sprite with status text."""
        sprite = create_sprite(status_text="custom status")
        assert sprite.status_text == "custom status"


class TestFormatSpriteStatus:
    """Tests for the format_sprite_status utility function."""

    def test_format_with_state(self):
        """Test formatting with state only."""
        result = format_sprite_status(SpriteState.IDLE)
        assert "😴" in result
        assert "dim" in result
        assert "zzz..." in result

    def test_format_with_custom_text(self):
        """Test formatting with custom text."""
        result = format_sprite_status(SpriteState.WORKING, "building project...")
        assert "⚡" in result
        assert "cyan" in result
        assert "building project..." in result

    def test_format_with_string_state(self):
        """Test formatting with string state."""
        result = format_sprite_status("alert", "error detected!")
        assert "⚠️" in result
        assert "red" in result
        assert "error detected!" in result

    def test_format_uses_state_color(self):
        """Test each state uses correct color in format."""
        for state in SpriteState:
            result = format_sprite_status(state)
            expected_color = STATE_COLORS[state]
            assert expected_color in result


class TestSpriteAnimationConsistency:
    """Tests to ensure animation frames are consistent."""

    def test_frames_have_similar_height(self):
        """Test animation frames have consistent line counts."""
        for state in SpriteState:
            frames = SPRITE_FRAMES[state]
            line_counts = [len(frame.split("\n")) for frame in frames]
            # All frames should have the same number of lines
            assert len(set(line_counts)) == 1, f"State {state} has inconsistent frame heights"

    def test_frames_are_distinct(self):
        """Test that frame 0 and frame 1 are different for animation effect."""
        for state in SpriteState:
            frames = SPRITE_FRAMES[state]
            assert frames[0] != frames[1], f"State {state} has identical frames"


class TestSpriteReactiveProperties:
    """Tests for reactive property behavior."""

    def test_state_reactive(self):
        """Test state is reactive (triggers watch)."""
        widget = SpriteWidget()
        widget.state = SpriteState.ALERT
        # Status should update to alert default
        assert widget.status_text == "attention!"

    def test_custom_status_preserved(self):
        """Test custom status text is preserved when set explicitly."""
        widget = SpriteWidget()
        widget.set_state(SpriteState.WORKING, status_text="my custom status")
        assert widget.status_text == "my custom status"
        # State change should not override custom text if we use set_state
        widget.set_state(SpriteState.DONE, status_text="still custom")
        assert widget.status_text == "still custom"
