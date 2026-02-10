#!/usr/bin/env python3
"""Verify demo mode data."""

import sys
sys.path.insert(0, 'src')

from openclaw_dash import demo

# Enable demo mode
demo.enable_demo_mode()

print("=== GATEWAY STATUS ===")
gateway = demo.mock_gateway_status()
print(f"Healthy: {gateway['healthy']}")
print(f"Uptime: {gateway['uptime']}")
print(f"Context: {gateway['context_pct']}%")
print()

print("=== REPOSITORIES ===")
repos = demo.mock_repos()
for repo in repos:
    print(f"{repo['name']}: status={repo['status']}, PRs={repo['prs']}, TODOs={repo.get('todos', 0)}, CI={repo['ci']}")
print()

print("=== SESSIONS ===")
sessions = demo.mock_sessions()
print(f"Total sessions: {len(sessions)}")
for sess in sessions:
    pct = (sess['totalTokens'] / sess['contextTokens']) * 100
    print(f"  {sess['displayName']}: {pct:.1f}% context")
print()

print("=== COSTS ===")
costs = demo.mock_cost_data()
print(f"Today: ${costs['today']['total']:.2f}")
print(f"All-time: ${costs['alltime']['total']:.2f}")
print()

print("=== ACTIVITY ===")
activity = demo.mock_activity()
print(f"Recent activities: {len(activity)}")
for act in activity[:3]:
    print(f"  - {act['action']}")
print()

print("=== ALERTS ===")
alerts = demo.mock_alerts()
print(f"Active alerts: {len(alerts)}")
for alert in alerts:
    print(f"  [{alert['severity']}] {alert['message']}")
print()

print("✅ Demo mode data looks good!")
