"""
Heltec V3 OLED Panel — subscribes to ocd/panel via WiFi MQTT
and renders system metrics on the built-in 128x64 SSD1306 OLED.

Board: Heltec WiFi LoRa 32 V3 (ESP32-S3 + SSD1306)
Framework: Arduino via PlatformIO

Required libraries (auto-installed by PlatformIO):
  - Heltec ESP32 Dev-Boards
  - PubSubClient (MQTT)
  - ArduinoJson

Config: edit the #defines below or override via platformio.ini build_flags.
"""

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Heltec.h>

// ===================== CONFIG =====================

// WiFi credentials — override via platformio.ini build_flags:
//   -DWIFI_SSID=\"MyNetwork\" -DWIFI_PASS=\"MyPassword\"
#ifndef WIFI_SSID
#define WIFI_SSID       "YOUR_WIFI_SSID"
#endif

#ifndef WIFI_PASS
#define WIFI_PASS       "YOUR_WIFI_PASSWORD"
#endif

// MQTT broker — override via build_flags:
//   -DMQTT_BROKER=\"192.168.1.100\" -DMQTT_PORT=1883
#ifndef MQTT_BROKER
#define MQTT_BROKER     "localhost"
#endif

#ifndef MQTT_PORT
#define MQTT_PORT       1883
#endif

// MQTT topic — must match [sinks.mqtt] topic in config.toml
#ifndef MQTT_TOPIC
#define MQTT_TOPIC      "ocd/panel"
#endif

// MQTT client ID — must be unique per device
#ifndef MQTT_CLIENT_ID
#define MQTT_CLIENT_ID  "ocd-heltec-panel"
#endif

// Reconnect intervals (ms)
#define WIFI_RETRY_MS   5000
#define MQTT_RETRY_MS   5000

// Display dimensions (Heltec V3 built-in OLED)
#define SCREEN_WIDTH    128
#define SCREEN_HEIGHT   64

// ===================== GLOBALS =====================

WiFiClient   wifiClient;
PubSubClient mqttClient(wifiClient);

// Latest metric values (updated from MQTT callback)
volatile float cpuPercent   = 0.0f;
volatile float memPercent   = 0.0f;
volatile int   alertCount   = 0;
char           statusText[16] = "---";
volatile unsigned long lastMsgTs = 0;

// ===================== FORWARD DECLS =====================

void connectWiFi();
void connectMQTT();
void mqttCallback(char* topic, byte* payload, unsigned int length);
void drawDisplay();
void drawBar(int x, int y, int w, int h, float pct, uint8_t color);

// ===================== SETUP =====================

void setup() {
    // Heltec V3 init: enable LoRa=false, Serial=true, OLED=true
    Heltec.begin(true /* LoRa */, true /* Serial */, true /* OLED */);
    Heltec.display->clear();
    Heltec.display->setTextAlignment(TEXT_ALIGN_CENTER);
    Heltec.display->setFont(ArialMT_Plain_16);
    Heltec.display->drawString(64, 20, "OCD Panel");
    Heltec.display->setFont(ArialMT_Plain_10);
    Heltec.display->drawString(64, 42, "Connecting...");
    Heltec.display->display();

    Serial.begin(115200);
    Serial.println("\n[ocd-panel] Booting...");

    connectWiFi();

    mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
    mqttClient.setCallback(mqttCallback);
    mqttClient.setBufferSize(1024);  // JSON payloads can be chunky

    connectMQTT();
}

// ===================== LOOP =====================

void loop() {
    // Ensure WiFi stays connected
    if (WiFi.status() != WL_CONNECTED) {
        connectWiFi();
    }

    // Ensure MQTT stays connected
    if (!mqttClient.connected()) {
        connectMQTT();
    }

    mqttClient.loop();
    drawDisplay();
    delay(100);  // 10 Hz refresh cap
}

// ===================== WIFI =====================

void connectWiFi() {
    Serial.printf("[ocd-panel] WiFi connecting to %s", WIFI_SSID);

    Heltec.display->clear();
    Heltec.display->setTextAlignment(TEXT_ALIGN_CENTER);
    Heltec.display->setFont(ArialMT_Plain_10);
    Heltec.display->drawString(64, 24, "WiFi: connecting...");
    Heltec.display->drawString(64, 38, WIFI_SSID);
    Heltec.display->display();

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASS);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 40) {
        delay(WIFI_RETRY_MS / 8);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("\n[ocd-panel] WiFi OK: %s\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println("\n[ocd-panel] WiFi FAILED, will retry");
    }
}

// ===================== MQTT =====================

void connectMQTT() {
    while (!mqttClient.connected()) {
        Serial.printf("[ocd-panel] MQTT connecting to %s:%d...", MQTT_BROKER, MQTT_PORT);

        Heltec.display->clear();
        Heltec.display->setTextAlignment(TEXT_ALIGN_CENTER);
        Heltec.display->setFont(ArialMT_Plain_10);
        Heltec.display->drawString(64, 24, "MQTT: connecting...");
        Heltec.display->drawString(64, 38, MQTT_BROKER);
        Heltec.display->display();

        if (mqttClient.connect(MQTT_CLIENT_ID)) {
            Serial.println(" OK");
            mqttClient.subscribe(MQTT_TOPIC);
            Serial.printf("[ocd-panel] Subscribed to %s\n", MQTT_TOPIC);
        } else {
            Serial.printf(" failed (rc=%d), retry in %ds\n",
                          mqttClient.state(), MQTT_RETRY_MS / 1000);
            delay(MQTT_RETRY_MS);
        }
    }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
    // Null-terminate the payload
    if (length >= 1024) return;  // sanity guard
    char jsonBuf[1024];
    memcpy(jsonBuf, payload, length);
    jsonBuf[length] = '\0';

    Serial.printf("[ocd-panel] RX %s: %s\n", topic, jsonBuf);

    // Parse JSON
    StaticJsonDocument<512> doc;
    DeserializationError err = deserializeJson(doc, jsonBuf);
    if (err) {
        Serial.printf("[ocd-panel] JSON parse error: %s\n", err.c_str());
        return;
    }

    // Extract metrics (with safe defaults)
    cpuPercent = doc.containsKey("cpu") ? doc["cpu"].as<float>() : cpuPercent;
    memPercent = doc.containsKey("mem") ? doc["mem"].as<float>() : memPercent;
    alertCount = doc.containsKey("alerts") ? doc["alerts"].as<int>() : alertCount;

    if (doc.containsKey("status")) {
        const char* s = doc["status"].as<const char*>();
        if (s) {
            strncpy(statusText, s, sizeof(statusText) - 1);
            statusText[sizeof(statusText) - 1] = '\0';
        }
    }

    lastMsgTs = millis();
}

// ===================== DISPLAY =====================

void drawBar(int x, int y, int w, int h, float pct, uint8_t color) {
    // Clamp
    if (pct < 0.0f) pct = 0.0f;
    if (pct > 100.0f) pct = 100.0f;

    int fillW = (int)((pct / 100.0f) * (float)w);

    // Outline
    Heltec.display->drawRect(x, y, w, h);

    // Fill
    if (fillW > 0) {
        Heltec.display->fillRect(x + 1, y + 1, fillW - 2 > 0 ? fillW - 2 : 1, h - 2);
    }
}

void drawDisplay() {
    Heltec.display->clear();
    Heltec.display->setTextAlignment(TEXT_ALIGN_LEFT);

    // --- CPU: large text top-left ---
    Heltec.display->setFont(ArialMT_Plain_24);
    char cpuBuf[8];
    snprintf(cpuBuf, sizeof(cpuBuf), "%.0f%%", cpuPercent);
    Heltec.display->drawString(0, 0, cpuBuf);

    // CPU label small
    Heltec.display->setFont(ArialMT_Plain_10);
    Heltec.display->drawString(65, 4, "CPU");

    // --- Memory bar ---
    Heltec.display->drawString(0, 28, "MEM");
    drawBar(28, 28, 72, 10, memPercent, WHITE);

    // Mem percentage text
    char memBuf[8];
    snprintf(memBuf, sizeof(memBuf), "%.0f%%", memPercent);
    Heltec.display->drawString(104, 28, memBuf);

    // --- Alert count ---
    Heltec.display->setFont(ArialMT_Plain_16);
    char alertBuf[12];
    snprintf(alertBuf, sizeof(alertBuf), "%d", alertCount);
    Heltec.display->drawString(0, 44, alertBuf);
    Heltec.display->setFont(ArialMT_Plain_10);
    Heltec.display->drawString(24, 50, "alerts");

    // --- Status text (right side) ---
    Heltec.display->setTextAlignment(TEXT_ALIGN_RIGHT);
    // Color-code: "ok" = normal, anything else = blink/invert hint
    Heltec.display->drawString(128, 50, statusText);

    // --- Stale indicator: flash if no data for 30s ---
    if (lastMsgTs > 0 && (millis() - lastMsgTs) > 30000) {
        Heltec.display->setTextAlignment(TEXT_ALIGN_CENTER);
        Heltec.display->setFont(ArialMT_Plain_10);
        // Blink via millis toggle
        if ((millis() / 500) % 2 == 0) {
            Heltec.display->drawString(64, 0, "STALE");
        }
    }

    Heltec.display->display();
}