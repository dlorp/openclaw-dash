"""
OBD2-DIAGNOSTIC-TUI - Session Logger
Log diagnostic sessions for analysis and troubleshooting
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class SessionEvent:
    """Single diagnostic event"""
    timestamp: str
    event_type: str  # CONNECT, DISCONNECT, DTC_READ, PARAM_READ, ERROR
    data: Dict
    

class DiagnosticLogger:
    """Log diagnostic sessions to JSON"""
    
    def __init__(self, log_dir: str = "./logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.current_session: Optional[str] = None
        self.events: List[SessionEvent] = []
        
    def start_session(self, protocol: str, vehicle_info: Dict):
        """Start new diagnostic session"""
        timestamp = datetime.now().isoformat()
        self.current_session = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.events = []
        
        # Log session start
        self.log_event("SESSION_START", {
            "protocol": protocol,
            "vehicle": vehicle_info,
            "started_at": timestamp
        })
        
    def log_event(self, event_type: str, data: Dict):
        """Log diagnostic event"""
        event = SessionEvent(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            data=data
        )
        self.events.append(event)
        
    def log_dtc(self, codes: List[str], descriptions: Dict[str, str]):
        """Log DTC read"""
        self.log_event("DTC_READ", {
            "count": len(codes),
            "codes": codes,
            "descriptions": descriptions
        })
        
    def log_parameters(self, params: Dict[str, float]):
        """Log parameter snapshot"""
        self.log_event("PARAM_SNAPSHOT", {
            "parameters": params
        })
        
    def log_error(self, error: str, context: Dict):
        """Log error condition"""
        self.log_event("ERROR", {
            "message": error,
            "context": context
        })
        
    def end_session(self, summary: Dict):
        """End session and write to file"""
        self.log_event("SESSION_END", {
            "ended_at": datetime.now().isoformat(),
            "summary": summary
        })
        
        if self.current_session:
            log_file = self.log_dir / self.current_session
            session_data = {
                "session_file": self.current_session,
                "events": [asdict(e) for e in self.events]
            }
            
            with open(log_file, 'w') as f:
                json.dump(session_data, f, indent=2)
                
            return str(log_file)
        return None
        
    def get_recent_sessions(self, count: int = 10) -> List[Dict]:
        """Get recent session summaries"""
        sessions = []
        log_files = sorted(self.log_dir.glob("session_*.json"), reverse=True)
        
        for log_file in log_files[:count]:
            try:
                with open(log_file) as f:
                    data = json.load(f)
                    
                # Extract summary
                start_event = next((e for e in data["events"] if e["event_type"] == "SESSION_START"), None)
                end_event = next((e for e in data["events"] if e["event_type"] == "SESSION_END"), None)
                dtc_events = [e for e in data["events"] if e["event_type"] == "DTC_READ"]
                
                if start_event and end_event:
                    sessions.append({
                        "file": log_file.name,
                        "started": start_event["timestamp"],
                        "ended": end_event["timestamp"],
                        "protocol": start_event["data"].get("protocol", "Unknown"),
                        "dtc_count": sum(e["data"]["count"] for e in dtc_events),
                        "event_count": len(data["events"])
                    })
            except Exception:
                continue
                
        return sessions


def export_csv(log_file: str, output_file: str):
    """Export session log to CSV for analysis"""
    import csv
    
    with open(log_file) as f:
        data = json.load(f)
    
    # Extract parameter snapshots
    param_events = [e for e in data["events"] if e["event_type"] == "PARAM_SNAPSHOT"]
    
    if not param_events:
        return
    
    # Get all parameter names
    all_params = set()
    for event in param_events:
        all_params.update(event["data"]["parameters"].keys())
    
    all_params = sorted(all_params)
    
    # Write CSV
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp"] + all_params)
        
        for event in param_events:
            row = [event["timestamp"]]
            params = event["data"]["parameters"]
            row.extend([params.get(p, "") for p in all_params])
            writer.writerow(row)


def analyze_session(log_file: str) -> Dict:
    """Analyze session for patterns and issues"""
    with open(log_file) as f:
        data = json.load(f)
    
    analysis = {
        "duration_seconds": 0,
        "dtc_codes": [],
        "error_count": 0,
        "parameter_stats": {}
    }
    
    # Calculate duration
    start = next((e for e in data["events"] if e["event_type"] == "SESSION_START"), None)
    end = next((e for e in data["events"] if e["event_type"] == "SESSION_END"), None)
    
    if start and end:
        start_time = datetime.fromisoformat(start["timestamp"])
        end_time = datetime.fromisoformat(end["timestamp"])
        analysis["duration_seconds"] = (end_time - start_time).total_seconds()
    
    # Collect DTCs
    for event in data["events"]:
        if event["event_type"] == "DTC_READ":
            analysis["dtc_codes"].extend(event["data"]["codes"])
        elif event["event_type"] == "ERROR":
            analysis["error_count"] += 1
    
    # Analyze parameters
    param_events = [e for e in data["events"] if e["event_type"] == "PARAM_SNAPSHOT"]
    if param_events:
        param_values = {}
        for event in param_events:
            for name, value in event["data"]["parameters"].items():
                if name not in param_values:
                    param_values[name] = []
                param_values[name].append(value)
        
        for name, values in param_values.items():
            analysis["parameter_stats"][name] = {
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "samples": len(values)
            }
    
    return analysis
