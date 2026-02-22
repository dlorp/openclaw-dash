"""
OBD2-DIAGNOSTIC-TUI - Protocol Definitions
Supports OBD-II (generic) and Subaru SSM1 protocols
Pure Python stdlib implementation
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from enum import Enum


class Protocol(Enum):
    """Supported diagnostic protocols"""
    OBD2 = "OBD-II"
    SSM1 = "Subaru SSM1"
    

@dataclass
class Parameter:
    """Diagnostic parameter definition"""
    pid: int
    name: str
    description: str
    unit: str
    formula: str  # Python expression to convert raw value
    min_val: float
    max_val: float
    protocol: Protocol
    

# OBD-II Mode 01 PIDs (Current Data)
OBD2_PIDS: Dict[int, Parameter] = {
    0x05: Parameter(
        pid=0x05,
        name="ECT",
        description="Engine Coolant Temperature",
        unit="°C",
        formula="A - 40",
        min_val=-40,
        max_val=215,
        protocol=Protocol.OBD2
    ),
    0x0C: Parameter(
        pid=0x0C,
        name="RPM",
        description="Engine RPM",
        unit="rpm",
        formula="((A * 256) + B) / 4",
        min_val=0,
        max_val=16383.75,
        protocol=Protocol.OBD2
    ),
    0x0D: Parameter(
        pid=0x0D,
        name="VSS",
        description="Vehicle Speed",
        unit="km/h",
        formula="A",
        min_val=0,
        max_val=255,
        protocol=Protocol.OBD2
    ),
    0x0F: Parameter(
        pid=0x0F,
        name="IAT",
        description="Intake Air Temperature",
        unit="°C",
        formula="A - 40",
        min_val=-40,
        max_val=215,
        protocol=Protocol.OBD2
    ),
    0x10: Parameter(
        pid=0x10,
        name="MAF",
        description="Mass Air Flow",
        unit="g/s",
        formula="((A * 256) + B) / 100",
        min_val=0,
        max_val=655.35,
        protocol=Protocol.OBD2
    ),
    0x11: Parameter(
        pid=0x11,
        name="TPS",
        description="Throttle Position",
        unit="%",
        formula="(A * 100) / 255",
        min_val=0,
        max_val=100,
        protocol=Protocol.OBD2
    ),
    0x2F: Parameter(
        pid=0x2F,
        name="FUEL",
        description="Fuel Tank Level",
        unit="%",
        formula="(A * 100) / 255",
        min_val=0,
        max_val=100,
        protocol=Protocol.OBD2
    ),
    0x46: Parameter(
        pid=0x46,
        name="AAT",
        description="Ambient Air Temperature",
        unit="°C",
        formula="A - 40",
        min_val=-40,
        max_val=215,
        protocol=Protocol.OBD2
    ),
    0x5C: Parameter(
        pid=0x5C,
        name="OIL_TEMP",
        description="Engine Oil Temperature",
        unit="°C",
        formula="A - 40",
        min_val=-40,
        max_val=215,
        protocol=Protocol.OBD2
    ),
}


# Subaru SSM1 Parameters (1992-1998 EJ engines)
SSM1_PIDS: Dict[int, Parameter] = {
    0x08: Parameter(
        pid=0x08,
        name="ECT",
        description="Engine Coolant Temperature",
        unit="°C",
        formula="A - 40",
        min_val=-40,
        max_val=215,
        protocol=Protocol.SSM1
    ),
    0x0E: Parameter(
        pid=0x0E,
        name="RPM",
        description="Engine RPM",
        unit="rpm",
        formula="A * 25",
        min_val=0,
        max_val=6375,
        protocol=Protocol.SSM1
    ),
    0x10: Parameter(
        pid=0x10,
        name="VSS",
        description="Vehicle Speed",
        unit="km/h",
        formula="A",
        min_val=0,
        max_val=255,
        protocol=Protocol.SSM1
    ),
    0x12: Parameter(
        pid=0x12,
        name="IAT",
        description="Intake Air Temperature",
        unit="°C",
        formula="A - 40",
        min_val=-40,
        max_val=215,
        protocol=Protocol.SSM1
    ),
    0x13: Parameter(
        pid=0x13,
        name="MAF",
        description="Mass Air Flow (voltage)",
        unit="V",
        formula="A / 51",
        min_val=0,
        max_val=5,
        protocol=Protocol.SSM1
    ),
    0x15: Parameter(
        pid=0x15,
        name="TPS",
        description="Throttle Position",
        unit="V",
        formula="A / 51",
        min_val=0,
        max_val=5,
        protocol=Protocol.SSM1
    ),
    0x1C: Parameter(
        pid=0x1C,
        name="BATT",
        description="Battery Voltage",
        unit="V",
        formula="A / 10",
        min_val=0,
        max_val=25.5,
        protocol=Protocol.SSM1
    ),
    0x23: Parameter(
        pid=0x23,
        name="KNOCK",
        description="Knock Correction",
        unit="°",
        formula="A / 2",
        min_val=0,
        max_val=127.5,
        protocol=Protocol.SSM1
    ),
}


def parse_value(param: Parameter, raw_bytes: bytes) -> float:
    """
    Parse raw diagnostic data using parameter formula
    
    Args:
        param: Parameter definition with formula
        raw_bytes: Raw byte data from ECU
        
    Returns:
        Parsed value in parameter units
    """
    # Create local namespace for formula evaluation
    A = raw_bytes[0] if len(raw_bytes) > 0 else 0
    B = raw_bytes[1] if len(raw_bytes) > 1 else 0
    C = raw_bytes[2] if len(raw_bytes) > 2 else 0
    D = raw_bytes[3] if len(raw_bytes) > 3 else 0
    
    try:
        value = eval(param.formula, {"__builtins__": {}}, {
            "A": A, "B": B, "C": C, "D": D
        })
        # Clamp to valid range
        return max(param.min_val, min(param.max_val, value))
    except Exception:
        return 0.0


def get_parameters(protocol: Protocol) -> Dict[int, Parameter]:
    """Get parameter definitions for protocol"""
    if protocol == Protocol.OBD2:
        return OBD2_PIDS
    elif protocol == Protocol.SSM1:
        return SSM1_PIDS
    else:
        return {}


def format_value(param: Parameter, value: float) -> str:
    """Format parameter value for display"""
    if param.unit in ["%", "°", "°C"]:
        return f"{value:.1f}{param.unit}"
    elif param.unit in ["rpm", "km/h", "g/s"]:
        return f"{value:.0f} {param.unit}"
    elif param.unit == "V":
        return f"{value:.2f}V"
    else:
        return f"{value:.2f} {param.unit}"
