#!/usr/bin/env python3
"""
Run flight log analysis for the specific flight log and event log files.
"""

import os
import sys
from flight_log_analyzer import FlightLogAnalyzer

def main():
    # Define file paths
    log_file = r"C:\Users\bdagn\Documents\GitHub\Ground-Station\GUI 2.1\logs\flight_log_2025-07-03_22-10-39.txt"
    event_log = r"C:\Users\bdagn\Documents\GitHub\Ground-Station\GUI 2.1\event_logs\event_log_2025-07-03_22-07-27.txt"
    output_dir = "analysis_output"
    
    print("Flight Log Analysis")
    print("="*50)
    print(f"Flight Log: {log_file}")
    print(f"Event Log: {event_log}")
    print(f"Output Directory: {output_dir}")
    print()
    
    # Check if files exist
    if not os.path.exists(log_file):
        print(f"Error: Flight log file not found: {log_file}")
        return
    
    if not os.path.exists(event_log):
        print(f"Warning: Event log file not found: {event_log}")
        event_log = None
    
    # Create analyzer and run analysis
    analyzer = FlightLogAnalyzer(log_file, event_log)
    analyzer.run_full_analysis(output_dir)
    
    print("\nAnalysis complete!")
    print(f"Check the '{output_dir}' directory for results:")
    print("- flight_path.kml (for Google Earth)")
    print("- plots/ directory with telemetry plots")
    print("- event_timeline.png (event timeline)")
    print("- flight_summary.txt (summary report)")

if __name__ == "__main__":
    main()
