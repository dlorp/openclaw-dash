#!/usr/bin/env python3
"""Take screenshot of the dashboard in demo mode."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


async def main():
    """Run dashboard in demo mode and take screenshot."""
    # Enable demo mode BEFORE importing app
    from openclaw_dash.demo import enable_demo_mode

    enable_demo_mode()

    from openclaw_dash.app import DashboardApp

    # Create output directory
    output_dir = Path(__file__).parent.parent / "docs" / "images"
    output_dir.mkdir(parents=True, exist_ok=True)

    app = DashboardApp()

    async with app.run_test(headless=True, size=(120, 40)) as pilot:
        # Wait for initial render
        await pilot.pause()

        # Take screenshot
        screenshot_path = output_dir / "dashboard.svg"
        app.save_screenshot(str(screenshot_path))
        print(f"Screenshot saved to {screenshot_path}")


if __name__ == "__main__":
    asyncio.run(main())
