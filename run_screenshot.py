#!/usr/bin/env python3
"""Run dashboard and take screenshot."""
import subprocess
import time
import os

# Open iTerm and run dashboard
script = '''
tell application "iTerm"
    activate
    create window with default profile
    tell current session of current window
        write text "cd ~/repos/openclaw-dash && source .venv/bin/activate && PYTHONPATH=src python -c 'from openclaw_dash.app import DashboardApp; DashboardApp().run()'"
    end tell
end tell
'''

# Run the AppleScript
subprocess.run(['osascript', '-e', script])

# Wait for app to render
time.sleep(3)

# Take screenshot
subprocess.run(['screencapture', '-w', 'screenshot.png'])

print("Screenshot captured to screenshot.png")
