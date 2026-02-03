"""Tests for the tamagotchi-style sprite widget."""

from openclaw_dash.widgets.sprite import (
    DEFAULT_STATUS_TEXT,
    SPRITES,
    STATE_COLORS,
    CompactSpriteWidget,
    SpriteState,
    SpriteWidget,
    create_sprite,
    format_sprite_status,
    get_sprite,
    get_sprite_art,
    get_state_color,
    parse_state,
)


class TestSpriteState:
    """Tests for SpriteState enum."""

    def test_sprite_state_values(self):
        """Test that all sprite state values are correct."""
        assert SpriteState.IDLE.value == "idle"
        assert SpriteState.SLEEP.value == "sleep"
        assert SpriteState.THINK.value == "think"
        assert SpriteState.WORK.value == "work"
        assert SpriteState.SPAWN.value == "spawn"
        assert SpriteState.DONE.value == "done"
        assert SpriteState.ALERT.value == "alert"

    def test_all_states_defined(self):
        """Test all expected states exist."""
        states = list(SpriteState)
        assert len(states) == 7


class TestParseState:
    """Tests for parse_state function."""

    def test_parse_valid_string(self):
        """Test parsing valid state strings."""
        assert parse_state("idle") == SpriteState.IDLE
        assert parse_state("sleep") == SpriteState.SLEEP
        assert parse_state("think") == SpriteState.THINK
        assert parse_state("work") == SpriteState.WORK
        assert parse_state("spawn") == SpriteState.SPAWN
        assert parse_state("done") == SpriteState.DONE
        assert parse_state("alert") == SpriteState.ALERT

    def test_parse_case_insensitive(self):
        """Test parsing is case insensitive."""
        assert parse_state("IDLE") == SpriteState.IDLE
        assert parse_state("Think") == SpriteState.THINK
        assert parse_state("WORK") == SpriteState.WORK

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


class TestSprites:
    """Tests for sprite ASCII art."""

    def test_all_states_have_sprites(self):
        """Test all states have sprites defined."""
        expected_states = ["idle", "sleep", "think", "work", "spawn", "done", "alert"]
        for state in expected_states:
            assert state in SPRITES
            assert len(SPRITES[state]) == 5  # 5 lines tall

    def test_sprites_are_5_chars_wide(self):
        """Test all sprite lines are 5 display chars wide."""
        for state, lines in SPRITES.items():
            for i, line in enumerate(lines):
                assert len(line) == 5, f"State {state} line {i} is {len(line)} chars, expected 5"

    def test_sprites_have_antenna(self):
        """Test sprites have the ¡ antenna on first line."""
        for state, lines in SPRITES.items():
            # Most sprites have antenna at position 2
            assert "¡" in lines[0], f"State {state} missing antenna ¡"

    def test_get_sprite_by_enum(self):
        """Test getting sprite by SpriteState enum."""
        sprite = get_sprite(SpriteState.IDLE)
        assert sprite == SPRITES["idle"]

    def test_get_sprite_by_string(self):
        """Test getting sprite by string."""
        sprite = get_sprite("work")
        assert sprite == SPRITES["work"]

    def test_get_sprite_invalid_returns_idle(self):
        """Test invalid state returns idle sprite."""
        sprite = get_sprite("invalid")
        assert sprite == SPRITES["idle"]

    def test_get_sprite_art(self):
        """Test get_sprite_art joins lines."""
        art = get_sprite_art(SpriteState.IDLE)
        expected = "\n".join(SPRITES["idle"])
        assert art == expected

    def test_idle_sprite_content(self):
        """Test idle sprite has expected content."""
        sprite = SPRITES["idle"]
        assert sprite[2] == "(o.o)"  # Eyes open
        assert sprite[3] == "|   |"  # Empty body
        assert sprite[4] == "`~~~'"  # Base

    def test_sleep_sprite_content(self):
        """Test sleep sprite has closed eyes."""
        sprite = SPRITES["sleep"]
        assert sprite[2] == "(-.-)"  # Eyes closed

    def test_think_sprite_content(self):
        """Test think sprite has question mark."""
        sprite = SPRITES["think"]
        assert sprite[3] == "| ? |"  # Question mark in body

    def test_work_sprite_content(self):
        """Test work sprite has wavy body."""
        sprite = SPRITES["work"]
        assert sprite[3] == "|~~~|"  # Activity in body

    def test_spawn_sprite_content(self):
        """Test spawn sprite has sub-agent indicator."""
        sprite = SPRITES["spawn"]
        assert "o" in sprite[0]  # Sub-agent spawning

    def test_done_sprite_content(self):
        """Test done sprite has happy face."""
        sprite = SPRITES["done"]
        assert sprite[2] == "(^.^)"  # Happy eyes

    def test_alert_sprite_content(self):
        """Test alert sprite has alert indicators."""
        sprite = SPRITES["alert"]
        assert "!" in sprite[0]  # Alert indicator
        assert sprite[2] == "(!.!)"  # Alert eyes


class TestStateColors:
    """Tests for state colors."""

    def test_all_states_have_colors(self):
        """Test all states have colors defined."""
        for state in SpriteState:
            assert state in STATE_COLORS

    def test_get_state_color(self):
        """Test get_state_color returns correct colors."""
        assert get_state_color(SpriteState.IDLE) == "white"
        assert get_state_color(SpriteState.SLEEP) == "dim"
        assert get_state_color(SpriteState.THINK) == "yellow"
        assert get_state_color(SpriteState.WORK) == "cyan"
        assert get_state_color(SpriteState.SPAWN) == "magenta"
        assert get_state_color(SpriteState.DONE) == "green"
        assert get_state_color(SpriteState.ALERT) == "red"


class TestDefaultStatusText:
    """Tests for default status text."""

    def test_all_states_have_default_text(self):
        """Test all states have default status text."""
        for state in SpriteState:
            assert state in DEFAULT_STATUS_TEXT

    def test_default_status_values(self):
        """Test default status text values."""
        assert DEFAULT_STATUS_TEXT[SpriteState.IDLE] == "ready"
        assert DEFAULT_STATUS_TEXT[SpriteState.SLEEP] == "zzz..."
        assert DEFAULT_STATUS_TEXT[SpriteState.THINK] == "hmm..."
        assert DEFAULT_STATUS_TEXT[SpriteState.WORK] == "working..."
        assert DEFAULT_STATUS_TEXT[SpriteState.SPAWN] == "spawning..."
        assert DEFAULT_STATUS_TEXT[SpriteState.DONE] == "done!"
        assert DEFAULT_STATUS_TEXT[SpriteState.ALERT] == "attention!"


class TestCreateSprite:
    """Tests for create_sprite factory function."""

    def test_create_default_sprite(self):
        """Test creating default sprite widget."""
        sprite = create_sprite()
        assert isinstance(sprite, SpriteWidget)
        assert sprite.state == SpriteState.IDLE

    def test_create_sprite_with_state(self):
        """Test creating sprite with specific state."""
        sprite = create_sprite(state=SpriteState.WORK)
        assert sprite.state == SpriteState.WORK

    def test_create_sprite_with_string_state(self):
        """Test creating sprite with string state."""
        sprite = create_sprite(state="alert")
        assert sprite.state == SpriteState.ALERT

    def test_create_compact_sprite(self):
        """Test creating compact sprite widget."""
        sprite = create_sprite(compact=True)
        assert isinstance(sprite, CompactSpriteWidget)


class TestFormatSpriteStatus:
    """Tests for format_sprite_status function."""

    def test_format_with_enum(self):
        """Test formatting with SpriteState enum."""
        result = format_sprite_status(SpriteState.WORK)
        assert "[cyan]" in result
        assert "(o.o)" in result  # Face from work sprite
        assert "working..." in result

    def test_format_with_string(self):
        """Test formatting with string state."""
        result = format_sprite_status("done")
        assert "[green]" in result
        assert "(^.^)" in result  # Face from done sprite

    def test_format_with_custom_text(self):
        """Test formatting with custom status text."""
        result = format_sprite_status(SpriteState.ALERT, "custom message")
        assert "(!.!)" in result  # Face from alert sprite
        assert "custom message" in result


class TestSpriteWidget:
    """Tests for SpriteWidget class."""

    def test_init_default(self):
        """Test default initialization."""
        widget = SpriteWidget()
        assert widget.state == SpriteState.IDLE
        assert widget.status_text == "ready"

    def test_init_with_state(self):
        """Test initialization with state."""
        widget = SpriteWidget(state=SpriteState.THINK)
        assert widget.state == SpriteState.THINK
        assert widget.status_text == "hmm..."

    def test_init_with_string_state(self):
        """Test initialization with string state."""
        widget = SpriteWidget(state="spawn")
        assert widget.state == SpriteState.SPAWN

    def test_init_with_custom_status(self):
        """Test initialization with custom status text."""
        widget = SpriteWidget(state=SpriteState.WORK, status_text="building...")
        assert widget.status_text == "building..."

    def test_set_state(self):
        """Test set_state method."""
        widget = SpriteWidget()
        widget.set_state(SpriteState.ALERT)
        assert widget.state == SpriteState.ALERT

    def test_set_state_with_text(self):
        """Test set_state with custom status text."""
        widget = SpriteWidget()
        widget.set_state(SpriteState.WORK, status_text="processing...")
        assert widget.state == SpriteState.WORK
        assert widget.status_text == "processing..."


class TestCompactSpriteWidget:
    """Tests for CompactSpriteWidget class."""

    def test_is_compact(self):
        """Test compact widget is in compact mode."""
        widget = CompactSpriteWidget()
        assert widget._compact is True

    def test_inherits_sprite_widget(self):
        """Test compact widget inherits from SpriteWidget."""
        widget = CompactSpriteWidget()
        assert isinstance(widget, SpriteWidget)
