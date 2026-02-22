#!/usr/bin/env python3
"""
OBD2-DIAGNOSTIC-TUI - Terminal OBD2/SSM1 Diagnostic Tool
Pure Python stdlib TUI for automotive diagnostics
Supports OBD-II generic and Subaru SSM1 protocols

Usage:
    ./obd2_tui.py                    # Interactive mode
    ./obd2_tui.py --demo              # Demo mode (simulated data)
    ./obd2_tui.py --port /dev/ttyUSB0 # Connect to adapter
    ./obd2_tui.py --analyze session.json  # Analyze log file
"""

import sys
import time
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from protocols import Protocol, Parameter, get_parameters, parse_value, format_value
from codes import DTC, lookup_code, parse_dtc_hex, format_dtc
from logger import DiagnosticLogger, analyze_session


# ANSI escape codes for terminal control
class Style:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Colors
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    
    # Background
    BG_BLACK = "\033[40m"
    BG_BLUE = "\033[44m"
    
    @staticmethod
    def clear_screen():
        print("\033[2J\033[H", end="")
        
    @staticmethod
    def move_cursor(row: int, col: int):
        print(f"\033[{row};{col}H", end="")
        
    @staticmethod
    def hide_cursor():
        print("\033[?25l", end="")
        
    @staticmethod
    def show_cursor():
        print("\033[?25h", end="")


@dataclass
class VehicleState:
    """Current vehicle diagnostic state"""
    protocol: Protocol
    connected: bool
    dtc_count: int
    dtc_codes: List[str]
    parameters: Dict[str, float]
    

class OBD2TUI:
    """Terminal UI for OBD2 diagnostics"""
    
    def __init__(self, demo_mode: bool = False):
        self.demo_mode = demo_mode
        self.running = False
        self.logger = DiagnosticLogger()
        self.state = VehicleState(
            protocol=Protocol.OBD2,
            connected=False,
            dtc_count=0,
            dtc_codes=[],
            parameters={}
        )
        
    def draw_header(self):
        """Draw application header"""
        Style.move_cursor(1, 1)
        print(f"{Style.BG_BLUE}{Style.WHITE}{Style.BOLD}", end="")
        print(" OBD2-DIAGNOSTIC-TUI v1.0 ".center(80), end="")
        print(f"{Style.RESET}")
        
        Style.move_cursor(2, 1)
        status = "CONNECTED" if self.state.connected else "DISCONNECTED"
        status_color = Style.GREEN if self.state.connected else Style.RED
        protocol_name = self.state.protocol.value
        
        print(f"{Style.DIM}Protocol: {Style.RESET}{protocol_name}  ", end="")
        print(f"{Style.DIM}Status: {status_color}{status}{Style.RESET}  ", end="")
        print(f"{Style.DIM}DTCs: {Style.YELLOW}{self.state.dtc_count}{Style.RESET}")
        
        # Separator
        Style.move_cursor(3, 1)
        print("─" * 80)
        
    def draw_gauge(self, row: int, col: int, param: Parameter, value: float, width: int = 30):
        """Draw ASCII gauge for parameter"""
        Style.move_cursor(row, col)
        
        # Calculate percentage
        range_size = param.max_val - param.min_val
        percent = (value - param.min_val) / range_size if range_size > 0 else 0
        percent = max(0, min(1, percent))
        
        # Draw gauge
        filled = int(percent * width)
        bar = "█" * filled + "░" * (width - filled)
        
        # Color based on value
        color = Style.GREEN
        if param.name in ["ECT", "OIL_TEMP"] and value > 100:
            color = Style.YELLOW
        elif param.name in ["ECT", "OIL_TEMP"] and value > 110:
            color = Style.RED
        elif param.name == "RPM" and value > 5000:
            color = Style.YELLOW
            
        formatted_val = format_value(param, value)
        
        print(f"{Style.BOLD}{param.name:6s}{Style.RESET} ", end="")
        print(f"{color}{bar}{Style.RESET} ", end="")
        print(f"{formatted_val:>12s}")
        
    def draw_parameters(self):
        """Draw live parameter display"""
        Style.move_cursor(5, 1)
        print(f"{Style.BOLD}LIVE DATA{Style.RESET}")
        
        params = get_parameters(self.state.protocol)
        
        # Priority parameters to display
        priority_pids = [0x0C, 0x0D, 0x05, 0x0F, 0x11, 0x10] if self.state.protocol == Protocol.OBD2 else \
                       [0x0E, 0x10, 0x08, 0x12, 0x15, 0x13]
        
        row = 6
        for pid in priority_pids:
            if pid in params:
                param = params[pid]
                value = self.state.parameters.get(param.name, 0.0)
                self.draw_gauge(row, 2, param, value)
                row += 1
                
    def draw_dtcs(self):
        """Draw DTC list"""
        start_row = 13
        Style.move_cursor(start_row, 1)
        print(f"{Style.BOLD}DIAGNOSTIC TROUBLE CODES{Style.RESET}")
        
        if not self.state.dtc_codes:
            Style.move_cursor(start_row + 1, 2)
            print(f"{Style.GREEN}✓ No trouble codes{Style.RESET}")
            return
            
        row = start_row + 1
        for code in self.state.dtc_codes[:5]:  # Show max 5 DTCs
            dtc = lookup_code(code)
            color = Style.RED if dtc.severity == "CRITICAL" else \
                   Style.YELLOW if dtc.severity == "WARNING" else Style.BLUE
            
            Style.move_cursor(row, 2)
            print(f"{color}▸{Style.RESET} {dtc.code:6s} {dtc.description[:55]}")
            row += 1
            
    def draw_footer(self):
        """Draw command footer"""
        Style.move_cursor(22, 1)
        print("─" * 80)
        
        Style.move_cursor(23, 1)
        commands = [
            ("R", "Read DTCs"),
            ("C", "Clear DTCs"),
            ("L", "View Logs"),
            ("Q", "Quit")
        ]
        
        for key, desc in commands:
            print(f"{Style.BOLD}{key}{Style.RESET}:{desc}  ", end="")
        print()
        
    def update_demo_data(self):
        """Update parameters with simulated data (demo mode)"""
        if not self.demo_mode:
            return
            
        # Simulate engine running
        base_rpm = 850
        rpm_variation = random.randint(-50, 50)
        self.state.parameters["RPM"] = base_rpm + rpm_variation
        
        self.state.parameters["ECT"] = 85 + random.uniform(-2, 2)
        self.state.parameters["VSS"] = random.randint(0, 5)
        self.state.parameters["IAT"] = 20 + random.uniform(-1, 1)
        self.state.parameters["TPS"] = 15 + random.uniform(-3, 3)
        self.state.parameters["MAF"] = 2.5 + random.uniform(-0.5, 0.5)
        
    def read_dtcs(self):
        """Read DTCs from ECU (or simulate in demo mode)"""
        if self.demo_mode:
            # Simulate some common DTCs
            self.state.dtc_codes = ["P0420", "P0171"]
            self.state.dtc_count = len(self.state.dtc_codes)
            
            descriptions = {code: lookup_code(code).description for code in self.state.dtc_codes}
            self.logger.log_dtc(self.state.dtc_codes, descriptions)
        
        return self.state.dtc_codes
        
    def clear_dtcs(self):
        """Clear DTCs from ECU"""
        if self.demo_mode:
            self.state.dtc_codes = []
            self.state.dtc_count = 0
            self.logger.log_event("DTC_CLEAR", {"cleared": True})
            
    def run(self):
        """Main application loop"""
        self.running = True
        
        try:
            Style.hide_cursor()
            
            # Start session
            vehicle_info = {
                "year": 1997,
                "make": "Subaru",
                "model": "Impreza",
                "engine": "EJ22"
            }
            
            protocol_name = self.state.protocol.value
            self.logger.start_session(protocol_name, vehicle_info)
            
            if self.demo_mode:
                self.state.connected = True
                time.sleep(0.5)
            
            last_update = time.time()
            
            while self.running:
                # Update display
                Style.clear_screen()
                self.draw_header()
                self.draw_parameters()
                self.draw_dtcs()
                self.draw_footer()
                
                # Update data periodically
                if time.time() - last_update > 0.2:
                    self.update_demo_data()
                    self.logger.log_parameters(self.state.parameters)
                    last_update = time.time()
                
                # Check for input (non-blocking in real implementation)
                time.sleep(0.1)
                
                # Demo mode: run for 10 seconds then exit
                if self.demo_mode and time.time() - last_update > 10:
                    break
                    
        except KeyboardInterrupt:
            pass
        finally:
            Style.show_cursor()
            Style.clear_screen()
            
            # End session
            summary = {
                "dtc_count": self.state.dtc_count,
                "parameters_logged": len(self.state.parameters)
            }
            log_file = self.logger.end_session(summary)
            
            if log_file:
                print(f"\n{Style.GREEN}✓{Style.RESET} Session logged to: {log_file}\n")


def main():
    """Entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="OBD2-DIAGNOSTIC-TUI - Terminal OBD2/SSM1 Diagnostic Tool"
    )
    parser.add_argument("--demo", action="store_true", help="Demo mode (simulated data)")
    parser.add_argument("--port", help="Serial port (e.g., /dev/ttyUSB0)")
    parser.add_argument("--analyze", help="Analyze session log file")
    parser.add_argument("--protocol", choices=["obd2", "ssm1"], default="obd2",
                       help="Diagnostic protocol")
    
    args = parser.parse_args()
    
    # Analyze mode
    if args.analyze:
        print(f"\n{Style.BOLD}Session Analysis: {args.analyze}{Style.RESET}\n")
        analysis = analyze_session(args.analyze)
        
        print(f"Duration: {analysis['duration_seconds']:.1f} seconds")
        print(f"DTCs Found: {len(analysis['dtc_codes'])}")
        if analysis['dtc_codes']:
            for code in set(analysis['dtc_codes']):
                dtc = lookup_code(code)
                print(f"  {format_dtc(dtc)}")
        
        print(f"\nParameter Statistics:")
        for name, stats in analysis['parameter_stats'].items():
            print(f"  {name:10s} min={stats['min']:6.1f} max={stats['max']:6.1f} avg={stats['avg']:6.1f}")
        
        return
    
    # Interactive mode
    tui = OBD2TUI(demo_mode=args.demo or not args.port)
    
    # Set protocol
    if args.protocol == "ssm1":
        tui.state.protocol = Protocol.SSM1
    
    print(f"\n{Style.BOLD}OBD2-DIAGNOSTIC-TUI{Style.RESET}")
    print(f"Protocol: {tui.state.protocol.value}")
    
    if args.demo:
        print(f"{Style.YELLOW}Running in DEMO mode{Style.RESET}\n")
        time.sleep(1)
    
    tui.run()


if __name__ == "__main__":
    main()
