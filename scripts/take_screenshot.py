#!/usr/bin/env python3
"""Take screenshot of the dashboard in demo mode.

Generates SVG screenshots for README documentation.
Requires larger terminal size (180x60) to ensure all panel content is visible.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Terminal size for screenshots - must be large enough for all content to render
# Smaller sizes cause panel content to be clipped
SCREENSHOT_WIDTH = 180
SCREENSHOT_HEIGHT = 60


async def take_screenshot(theme: str | None = None) -> Path:
    """Take a screenshot with the specified theme.

    Args:
        theme: Theme name to apply, or None for default.

    Returns:
        Path to the saved screenshot.
    """
    from openclaw_dash.app import DashboardApp

    output_dir = Path(__file__).parent.parent / "docs" / "images"
    output_dir.mkdir(parents=True, exist_ok=True)

    app = DashboardApp()

    async with app.run_test(headless=True, size=(SCREENSHOT_WIDTH, SCREENSHOT_HEIGHT)) as pilot:
        # Wait for initial render and data refresh
        await pilot.pause()
        await pilot.pause()
        await pilot.pause()

        # Apply theme if specified
        if theme:
            app.theme = theme
            await pilot.pause()

        # Determine output filename
        if theme and theme != "dark":
            screenshot_path = output_dir / f"dashboard_{theme}.svg"
        else:
            screenshot_path = output_dir / "dashboard.svg"

        app.save_screenshot(str(screenshot_path))
        print(f"Screenshot saved to {screenshot_path}")
        return screenshot_path


async def main():
    """Generate all dashboard screenshots."""
    # Enable demo mode BEFORE importing app
    from openclaw_dash.demo import enable_demo_mode

    enable_demo_mode()

    # Generate default (dark) theme screenshot
    await take_screenshot()

    # Generate phosphor theme screenshot
    await take_screenshot("phosphor")

    print("\nAll screenshots generated successfully!")


if __name__ == "__main__":
    asyncio.run(main())
