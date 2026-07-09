# OCD Panel — Heltec V3 OLED Firmware

MQTT-driven status display for hermes-dash.

## What it does

Subscribes to `ocd/panel` via WiFi MQTT and renders metrics on the
Heltec V3's built-in 128x64 SSD1306 OLED:

- **CPU%** — large text, top-left
- **Memory bar** — graphical fill bar with percentage
- **Alert count** — number of active alerts
- **Status** — "ok" or error state from gateway
- **STALE indicator** — flashes if no data received for 30s

## Hardware

- Heltec WiFi LoRa 32 V3 (ESP32-S3 + SSD1306 128x64 OLED)
- No external wiring needed — uses built-in OLED

## Build & Upload

```bash
# Install PlatformIO CLI (if needed)
pip install platformio

# Build
cd firmware/heltec-panel
pio run

# Upload (USB connected)
pio run --target upload

# Serial monitor
pio device monitor
```

## Configuration

Edit `platformio.ini` build_flags (uncomment and set values):

```ini
build_flags =
    -DWIFI_SSID=\"YourNetwork\"
    -DWIFI_PASS=\"YourPassword\"
    -DMQTT_BROKER=\"192.168.1.100\"
    -DMQTT_PORT=1883
    -DMQTT_TOPIC=\"ocd/panel\"
```

Or edit the `#define` defaults in `src/main.cpp`.

## MQTT Payload Format

The panel expects JSON on `ocd/panel`:

```json
{
  "cpu": 45.2,
  "mem": 78.1,
  "alerts": 3,
  "status": "ok",
  "ts": 1720000000.0
}
```

The hermes-dash MQTT sink produces this format automatically.

## Auto-reconnect

Both WiFi and MQTT connections auto-reconnect on drop. The display
shows connection status during reconnect attempts.