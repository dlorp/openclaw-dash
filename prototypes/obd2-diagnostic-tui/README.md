# OBD2-DIAGNOSTIC-TUI

Terminal-based OBD-II and Subaru SSM1 diagnostic tool for automotive troubleshooting.

**Pure Python stdlib implementation** — zero external dependencies for core functionality.

```
┌─ OBD2-DIAGNOSTIC-TUI v1.0 ────────────────────────────────────────────────────┐
│ Protocol: OBD-II  Status: CONNECTED  DTCs: 2                                  │
├───────────────────────────────────────────────────────────────────────────────┤
│ LIVE DATA                                                                     │
│  RPM     ████████░░░░░░░░░░░░░░░░░░  850 rpm                                 │
│  VSS     ░░░░░░░░░░░░░░░░░░░░░░░░░░    0 km/h                                │
│  ECT     ███████████████░░░░░░░░░░░   85.2°C                                 │
│  IAT     ████████░░░░░░░░░░░░░░░░░░   20.1°C                                 │
│  TPS     ████░░░░░░░░░░░░░░░░░░░░░░   15.3%                                  │
│  MAF     ██░░░░░░░░░░░░░░░░░░░░░░░░   2.4 g/s                                │
│                                                                               │
│ DIAGNOSTIC TROUBLE CODES                                                     │
│  ▸ P0420  Catalyst System Efficiency Below Threshold (Bank 1)                │
│  ▸ P0171  System Too Lean (Bank 1)                                           │
├───────────────────────────────────────────────────────────────────────────────┤
│ R:Read DTCs  C:Clear DTCs  L:View Logs  Q:Quit                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

## Features

**Protocol Support:**
- OBD-II generic (all vehicles 1996+)
- Subaru SSM1 (1992-1998 EJ engines including EJ22)

**Diagnostic Functions:**
- Real-time parameter monitoring (RPM, temp, speed, throttle, MAF)
- DTC reading with detailed descriptions
- DTC clearing
- Session logging (JSON format)
- Freeze frame data capture
- Parameter trend analysis

**Terminal-Native UI:**
- ASCII gauges with color-coded warnings
- Live updating dashboard
- Minimal dependencies (pure stdlib)
- Runs over SSH, in tmux/screen

## Installation

```bash
cd ~/repos/openclaw-dash/prototypes/obd2-diagnostic-tui
chmod +x obd2_tui.py

# Demo mode (no hardware required)
./obd2_tui.py --demo

# With OBD2 adapter
./obd2_tui.py --port /dev/ttyUSB0
```

**Hardware Requirements (for real use):**
- ELM327-compatible OBD2 adapter (USB or Bluetooth)
- For Subaru SSM1: Tactrix OpenPort 2.0 or similar (dlorp should use Evoscan)

## Usage

### Demo Mode
```bash
./obd2_tui.py --demo
```
Simulates live engine data for testing/development.

### Real Hardware
```bash
# OBD-II (1997+ Subaru)
./obd2_tui.py --port /dev/ttyUSB0 --protocol obd2

# SSM1 (1992-1998 Subaru)
./obd2_tui.py --port /dev/ttyUSB0 --protocol ssm1
```

### Analyze Logs
```bash
./obd2_tui.py --analyze logs/session_20260222_001530.json
```

Outputs parameter statistics, DTCs found, and session duration.

## File Structure

```
obd2-diagnostic-tui/
├── obd2_tui.py      # Main TUI application
├── protocols.py     # OBD-II and SSM1 protocol definitions
├── codes.py         # DTC database (generic + Subaru-specific)
├── logger.py        # Session logging and analysis
├── logs/            # Diagnostic session logs (JSON)
└── README.md        # This file
```

## Architecture

### Protocol Layer (`protocols.py`)
Defines parameter PIDs, formulas, and parsing logic for both OBD-II and SSM1.

**Example parameter:**
```python
Parameter(
    pid=0x0C,
    name="RPM",
    description="Engine RPM",
    unit="rpm",
    formula="((A * 256) + B) / 4",  # Convert raw bytes to RPM
    min_val=0,
    max_val=16383.75,
    protocol=Protocol.OBD2
)
```

### DTC Database (`codes.py`)
Generic OBD-II codes + Subaru-specific P1xxx codes.

**Example DTC:**
```python
DTC(
    code="P0171",
    description="System Too Lean (Bank 1)",
    severity="WARNING",
    category="Fuel System",
    likely_causes=[
        "Vacuum leak",
        "Low fuel pressure",
        "Dirty fuel injectors",
        "Failed O2 sensor"
    ]
)
```

### Session Logger (`logger.py`)
Records all diagnostic events to JSON for later analysis.

**Logged events:**
- `SESSION_START` - Connection established
- `DTC_READ` - Trouble codes read
- `PARAM_SNAPSHOT` - Parameter values at timestamp
- `ERROR` - Communication errors
- `SESSION_END` - Disconnection with summary

### TUI (`obd2_tui.py`)
Terminal interface using ANSI escape codes:
- Real-time parameter gauges
- Color-coded warnings (temp/RPM thresholds)
- DTC display with severity indicators
- Non-blocking input handling

## Integration with r3LAY

This tool provides the **automotive diagnostic foundation** for the r3LAY automotive module (PR #108).

**Potential integration points:**

1. **DTC Knowledge Base**
   - Export `codes.py` definitions to r3LAY's axiom format
   - Community-sourced diagnostic flowcharts
   - Real-world fix success rates

2. **Session Analysis**
   - Import logged sessions into r3LAY for pattern analysis
   - Cross-reference DTCs with forum discussions
   - Identify recurring issues (freeze frame correlation)

3. **Subaru EJ22 Specifics**
   - dlorp's '97 Impreza diagnostic history
   - EJ22-specific maintenance patterns
   - SSM1 protocol quirks and workarounds

4. **Evoscan Companion**
   - Lighter alternative for quick checks
   - SSH-accessible (remote diagnostics)
   - Log format compatible with Evoscan exports

## Data Export

### CSV Export (for analysis in Excel/Python)
```python
from logger import export_csv

export_csv("logs/session_20260222_001530.json", "output.csv")
```

Produces timestamped parameter data:
```
timestamp,RPM,ECT,VSS,TPS,MAF
2026-02-22T00:15:30,850,85.2,0,15.3,2.4
2026-02-22T00:15:31,855,85.3,0,15.1,2.5
...
```

### Session Analysis
```python
from logger import analyze_session

analysis = analyze_session("logs/session_20260222_001530.json")

# Output:
{
    "duration_seconds": 180,
    "dtc_codes": ["P0420", "P0171"],
    "error_count": 0,
    "parameter_stats": {
        "RPM": {"min": 800, "max": 900, "avg": 852, "samples": 900},
        "ECT": {"min": 84.5, "max": 86.1, "avg": 85.3, "samples": 900}
    }
}
```

## Technical Details

### OBD-II Mode 01 PIDs
- `0x05` - Engine Coolant Temperature
- `0x0C` - Engine RPM
- `0x0D` - Vehicle Speed
- `0x0F` - Intake Air Temperature
- `0x10` - Mass Air Flow
- `0x11` - Throttle Position
- `0x2F` - Fuel Level
- `0x5C` - Engine Oil Temperature

### Subaru SSM1 Addresses
- `0x08` - Coolant Temperature
- `0x0E` - Engine RPM (25 RPM/unit)
- `0x10` - Vehicle Speed
- `0x12` - Intake Air Temperature
- `0x13` - MAF (voltage)
- `0x15` - TPS (voltage)
- `0x1C` - Battery Voltage
- `0x23` - Knock Correction

### DTC Format
Standard 5-character format: `[Type][Source][Digit][Digit][Digit]`

**Type:**
- `P` - Powertrain (engine/transmission)
- `C` - Chassis (ABS/suspension)
- `B` - Body (airbags/climate)
- `U` - Network (CAN bus)

**Source:**
- `0` - Generic (SAE J2012)
- `1` - Manufacturer-specific

## Limitations

**Current implementation:**
- Demo mode only (no real serial communication yet)
- Limited to Mode 01 (live data) and Mode 03 (read DTCs)
- No Mode 04 (clear DTCs) implementation for hardware
- Single ECU support (no multi-ECU queries)

**To add real hardware support:**
1. Install `pyserial`: `pip install pyserial`
2. Implement ELM327 command protocol in `protocols.py`
3. Add serial communication layer to `obd2_tui.py`

## Real-World Use Case: dlorp's 1997 Impreza

**Vehicle:** 1997 Subaru Impreza (EJ22 engine)  
**Current tool:** Evoscan (Windows, proprietary)  
**Goal:** Local diagnostics, SSH-accessible, session logging

**Workflow:**
1. Connect Tactrix OpenPort 2.0 to OBD2 port
2. Run `./obd2_tui.py --port /dev/ttyUSB0 --protocol ssm1`
3. Monitor coolant temp, knock correction during spirited driving
4. Log sessions for pattern analysis (winter sliding sessions)
5. Export to CSV, analyze temperature trends vs outside temp

**Why SSM1 over OBD-II for '97 Impreza:**
- SSM1 provides more Subaru-specific parameters (knock correction!)
- Lower-level ECU access
- Better for performance monitoring/tuning

## Future Enhancements

- [ ] Real ELM327 serial communication
- [ ] Mode 04 (clear DTCs) for hardware
- [ ] Mode 06 (test results) - O2 sensor monitoring
- [ ] Graphical parameter plots (ASCII spark lines)
- [ ] Real-time knock detection alerts
- [ ] Integration with r3LAY automotive module
- [ ] Multi-ECU support (engine + transmission)
- [ ] Bluetooth OBD2 adapter support

## Cost Estimate (for dlorp)

**Hardware needed:**
- Tactrix OpenPort 2.0: ~$170 (if not owned)
- OR cheap ELM327 clone: ~$10-20 (OBD-II only)

**Total software cost:** $0 (pure Python stdlib)

**vs Evoscan:**
- Evoscan: Free, but Windows-only
- OBD2-TUI: Free, cross-platform, SSH-accessible

## See Also

- [Evoscan](http://www.tactrix.com/index.php?option=com_content&view=article&id=48) - Windows OBD2/SSM tool
- [r3LAY Automotive Module PR #108](https://github.com/dlorp/r3LAY/pull/108) - Integration target
- [SSM1 Protocol Spec](https://romraider.com/RomRaider/SSMProtocol) - Technical reference

---

**Built:** 2026-02-22 00:00 AKST (Session 2/6)  
**Lines:** ~2,300 code + ~500 docs  
**Dependencies:** Pure Python stdlib  
**Constraint:** Terminal-native, SSH-accessible, zero external deps
