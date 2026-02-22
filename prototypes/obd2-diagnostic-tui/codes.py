"""
OBD2-DIAGNOSTIC-TUI - Diagnostic Trouble Code Database
DTC definitions for OBD-II generic and Subaru-specific codes
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum


class DTCType(Enum):
    """DTC code type (first character)"""
    POWERTRAIN = "P"  # Engine and transmission
    CHASSIS = "C"      # ABS, suspension, steering
    BODY = "B"         # Airbags, climate control, doors
    NETWORK = "U"      # CAN bus communication


class DTCSource(Enum):
    """DTC source (second character)"""
    GENERIC = "0"      # SAE standard
    MANUFACTURER = "1" # Manufacturer-specific
    

@dataclass
class DTC:
    """Diagnostic Trouble Code definition"""
    code: str
    description: str
    severity: str  # CRITICAL, WARNING, INFO
    category: str
    likely_causes: List[str]
    

# OBD-II Generic Powertrain Codes (P0xxx)
GENERIC_CODES: Dict[str, DTC] = {
    "P0011": DTC(
        code="P0011",
        description="Camshaft Position - Timing Over-Advanced (Bank 1)",
        severity="WARNING",
        category="VVT/Timing",
        likely_causes=[
            "VVT solenoid malfunction",
            "Low oil level/pressure",
            "Timing chain stretched",
            "ECU software issue"
        ]
    ),
    "P0101": DTC(
        code="P0101",
        description="Mass Air Flow Circuit Range/Performance",
        severity="WARNING",
        category="Air Intake",
        likely_causes=[
            "Dirty/failed MAF sensor",
            "Air leak after MAF",
            "Clogged air filter",
            "Vacuum leak"
        ]
    ),
    "P0171": DTC(
        code="P0171",
        description="System Too Lean (Bank 1)",
        severity="WARNING",
        category="Fuel System",
        likely_causes=[
            "Vacuum leak",
            "Low fuel pressure",
            "Dirty fuel injectors",
            "Failed O2 sensor",
            "MAF sensor dirty"
        ]
    ),
    "P0301": DTC(
        code="P0301",
        description="Cylinder 1 Misfire Detected",
        severity="CRITICAL",
        category="Ignition",
        likely_causes=[
            "Bad spark plug",
            "Failed ignition coil",
            "Low compression",
            "Fuel injector clogged",
            "Vacuum leak"
        ]
    ),
    "P0420": DTC(
        code="P0420",
        description="Catalyst System Efficiency Below Threshold (Bank 1)",
        severity="WARNING",
        category="Emissions",
        likely_causes=[
            "Failed catalytic converter",
            "O2 sensor degraded",
            "Exhaust leak",
            "Rich/lean condition"
        ]
    ),
    "P0505": DTC(
        code="P0505",
        description="Idle Air Control System Malfunction",
        severity="INFO",
        category="Idle Control",
        likely_causes=[
            "IAC valve stuck",
            "Carbon buildup in throttle body",
            "Vacuum leak",
            "Throttle position sensor issue"
        ]
    ),
}


# Subaru-Specific Codes (P1xxx for EJ22/EJ25)
SUBARU_CODES: Dict[str, DTC] = {
    "P1400": DTC(
        code="P1400",
        description="Fuel Tank Pressure Control Solenoid",
        severity="INFO",
        category="EVAP",
        likely_causes=[
            "EVAP solenoid failure",
            "Wiring issue",
            "Gas cap loose/damaged"
        ]
    ),
    "P1410": DTC(
        code="P1410",
        description="Secondary Air System",
        severity="INFO",
        category="Emissions",
        likely_causes=[
            "Air pump failure",
            "Check valve stuck",
            "Vacuum leak in secondary air"
        ]
    ),
    "P1507": DTC(
        code="P1507",
        description="Idle Air Control System RPM Higher Than Expected",
        severity="INFO",
        category="Idle Control",
        likely_causes=[
            "IAC valve stuck open",
            "Vacuum leak",
            "Throttle position issue"
        ]
    ),
    "P1700": DTC(
        code="P1700",
        description="AT Control System (Automatic Transmission)",
        severity="WARNING",
        category="Transmission",
        likely_causes=[
            "TCU communication failure",
            "AT fluid low/dirty",
            "Solenoid malfunction"
        ]
    ),
}


# Freeze Frame Data Structure
@dataclass
class FreezeFrame:
    """Snapshot of sensor data when DTC was set"""
    dtc: str
    rpm: int
    speed: int
    coolant_temp: int
    intake_temp: int
    fuel_status: str
    load: int
    timestamp: str
    

def lookup_code(code: str) -> DTC:
    """
    Look up DTC description
    
    Args:
        code: DTC code (e.g., "P0420")
        
    Returns:
        DTC object or generic unknown code
    """
    # Try generic codes first
    if code in GENERIC_CODES:
        return GENERIC_CODES[code]
    
    # Try manufacturer-specific
    if code in SUBARU_CODES:
        return SUBARU_CODES[code]
    
    # Unknown code - create generic entry
    return DTC(
        code=code,
        description="Unknown DTC - Check Service Manual",
        severity="WARNING",
        category="Unknown",
        likely_causes=["Consult Subaru service documentation"]
    )


def parse_dtc_hex(data: bytes) -> List[str]:
    """
    Parse DTCs from raw hex response
    OBD-II Mode 03 returns DTCs as 2-byte pairs
    
    Format: [type][digit][digit][digit][digit]
    First byte: [type nibble][digit 1 nibble]
    Second byte: [digit 2 nibble][digit 3 nibble]
    
    Args:
        data: Raw bytes from Mode 03 response
        
    Returns:
        List of DTC codes
    """
    codes = []
    
    # Process in 2-byte pairs
    for i in range(0, len(data), 2):
        if i + 1 >= len(data):
            break
            
        high = data[i]
        low = data[i + 1]
        
        # Skip empty codes (0x0000)
        if high == 0 and low == 0:
            continue
        
        # Extract type from high nibble
        type_bits = (high >> 6) & 0x03
        type_map = {0: "P", 1: "C", 2: "B", 3: "U"}
        code_type = type_map.get(type_bits, "P")
        
        # Extract source (generic vs manufacturer)
        source = "1" if (high >> 4) & 0x03 else "0"
        
        # Extract digits
        digit1 = (high >> 4) & 0x0F
        digit2 = high & 0x0F
        digit3 = (low >> 4) & 0x0F
        digit4 = low & 0x0F
        
        # Format code
        code = f"{code_type}{source}{digit2:X}{digit3:X}{digit4:X}"
        codes.append(code)
    
    return codes


def get_severity_color(severity: str) -> str:
    """Get ANSI color code for severity level"""
    colors = {
        "CRITICAL": "\033[91m",  # Red
        "WARNING": "\033[93m",   # Yellow
        "INFO": "\033[94m",      # Blue
    }
    return colors.get(severity, "\033[0m")


def format_dtc(dtc: DTC, show_causes: bool = False) -> str:
    """Format DTC for terminal display"""
    color = get_severity_color(dtc.severity)
    reset = "\033[0m"
    
    output = f"{color}[{dtc.code}]{reset} {dtc.description}\n"
    output += f"  Category: {dtc.category} | Severity: {dtc.severity}\n"
    
    if show_causes:
        output += "  Likely Causes:\n"
        for cause in dtc.likely_causes:
            output += f"    • {cause}\n"
    
    return output
