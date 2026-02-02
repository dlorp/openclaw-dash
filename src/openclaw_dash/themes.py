"""Theme definitions for the dashboard TUI.

Textual themes use CSS variables for colors. These themes define the
core design system variables that panels and widgets use.
"""

from textual.theme import Theme

# =============================================================================
# OpenClaw Brand Colors
# =============================================================================
# These are the canonical brand colors used throughout the dashboard.
# Reference these constants instead of hardcoding hex values.


class BrandColors:
    """OpenClaw brand color palette."""

    GRANITE_GRAY = "#636764"  # Borders, muted elements
    DARK_ORANGE = "#FB8B24"  # Warnings, important actions
    TITANIUM_YELLOW = "#F4E409"  # Highlights, focus states
    MEDIUM_TURQUOISE = "#50D8D7"  # Success, online status
    ROYAL_BLUE_LIGHT = "#3B60E4"  # Primary, links


# Expose individual colors for convenience
GRANITE_GRAY = BrandColors.GRANITE_GRAY
DARK_ORANGE = BrandColors.DARK_ORANGE
TITANIUM_YELLOW = BrandColors.TITANIUM_YELLOW
MEDIUM_TURQUOISE = BrandColors.MEDIUM_TURQUOISE
ROYAL_BLUE_LIGHT = BrandColors.ROYAL_BLUE_LIGHT


# =============================================================================
# Theme Definitions
# =============================================================================

# Dark theme - default, easy on the eyes
DARK_THEME = Theme(
    name="dark",
    primary="#50D8D7",  # Medium Turquoise
    secondary="#3B60E4",  # Royal Blue Light
    accent="#FB8B24",  # Dark Orange
    foreground="#E0E0E0",
    background="#1A1A1A",
    surface="#2A2A2A",
    panel="#333333",
    success="#50D8D7",  # Use brand turquoise for success
    warning="#FB8B24",  # Use brand orange for warnings
    error="#FF5252",
    dark=True,
)

# Light theme - for daylight work
LIGHT_THEME = Theme(
    name="light",
    primary="#3B60E4",  # Royal Blue Light
    secondary="#50D8D7",  # Medium Turquoise
    accent="#FB8B24",  # Dark Orange
    foreground="#1A1A1A",
    background="#F5F5F5",
    surface="#FFFFFF",
    panel="#E8E8E8",
    success="#00C853",
    warning="#FFB300",
    error="#D32F2F",
    dark=False,
)

# Hacker green - for that matrix vibe
HACKER_THEME = Theme(
    name="hacker",
    primary="#00FF00",  # Classic green
    secondary="#00CC00",  # Darker green
    accent="#00FF66",  # Bright green accent
    foreground="#00FF00",
    background="#0A0A0A",
    surface="#0F1A0F",
    panel="#0D1F0D",
    success="#00FF00",
    warning="#CCFF00",
    error="#FF3300",
    dark=True,
)

# List of available themes in cycle order
THEMES = [DARK_THEME, LIGHT_THEME, HACKER_THEME]
THEME_NAMES = [t.name for t in THEMES]


def get_theme(name: str) -> Theme:
    """Get a theme by name."""
    for theme in THEMES:
        if theme.name == name:
            return theme
    return DARK_THEME


def next_theme(current: str) -> str:
    """Get the next theme name in the cycle."""
    try:
        idx = THEME_NAMES.index(current)
        return THEME_NAMES[(idx + 1) % len(THEME_NAMES)]
    except ValueError:
        return THEME_NAMES[0]
