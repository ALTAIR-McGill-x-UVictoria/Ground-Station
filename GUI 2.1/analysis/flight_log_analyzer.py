#!/usr/bin/env python3
"""
Flight Log Analyzer
Analyzes flight log data, creates Google Earth KML files, and generates analysis plots.
"""

import os
import sys
import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import numpy as np
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
import argparse


class FlightLogAnalyzer:
    """Main class for analyzing flight log data"""
    
    def __init__(self, log_file_path, event_log_path=None):
        """
        Initialize the analyzer
        
        Args:
            log_file_path: Path to the flight log file
            event_log_path: Path to the event log file (optional)
        """
        self.log_file_path = log_file_path
        self.event_log_path = event_log_path
        self.flight_data = None
        self.event_data = None
        self.start_time = None
        
    def parse_flight_log(self):
        """Parse the flight log file and extract FC packet data"""
        print("Parsing flight log...")
        
        fc_packets = []
        gs_packets = []
        
        with open(self.log_file_path, 'r') as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                    
                # Extract timestamp and packet type
                timestamp_match = re.match(r'\[(\d{2}:\d{2}:\d{2}\.\d{3})\]\s+(.+)', line)
                if not timestamp_match:
                    continue
                    
                timestamp_str = timestamp_match.group(1)
                packet_content = timestamp_match.group(2)
                
                # Convert timestamp to datetime
                try:
                    # Assuming log date is from the filename
                    log_date = self._extract_date_from_filename()
                    timestamp = datetime.strptime(f"{log_date} {timestamp_str}", "%Y-%m-%d %H:%M:%S.%f")
                    
                    if self.start_time is None:
                        self.start_time = timestamp
                        
                except ValueError:
                    continue
                
                # Parse FC packets
                if packet_content.startswith('FC:'):
                    fc_data = self._parse_fc_packet(packet_content[3:], timestamp)
                    if fc_data:
                        fc_packets.append(fc_data)
                        
                # Parse GS packets  
                elif packet_content.startswith('GS:'):
                    gs_data = self._parse_gs_packet(packet_content[3:], timestamp)
                    if gs_data:
                        gs_packets.append(gs_data)
        
        # Convert to DataFrames
        self.flight_data = pd.DataFrame(fc_packets) if fc_packets else pd.DataFrame()
        self.gs_data = pd.DataFrame(gs_packets) if gs_packets else pd.DataFrame()
        
        # Calculate vertical speed if we have flight data
        if not self.flight_data.empty:
            self._calculate_vertical_speed()
        
        print(f"Parsed {len(fc_packets)} FC packets and {len(gs_packets)} GS packets")
        
        return self.flight_data
    
    def _extract_date_from_filename(self):
        """Extract date from the log filename"""
        # Extract date from filename like 'flight_log_2025-07-03_22-10-39.txt'
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', self.log_file_path)
        if date_match:
            return date_match.group(1)
        return "2025-07-03"  # Default fallback
    
    def _parse_fc_packet(self, packet_str, timestamp):
        """Parse Flight Computer packet according to telemetry_controller.py structure"""
        values = packet_str.split(',')
        
        if len(values) < 20:
            return None
            
        try:
            # Parse according to the telemetry controller structure
            data = {
                'timestamp': timestamp,
                'time_elapsed': (timestamp - self.start_time).total_seconds() if self.start_time else 0,
                'ack': self._safe_int(values, 0),
                'rssi': self._safe_int(values, 1),
                'snr': self._safe_int(values, 2),
                'fc_boot_time_ms': self._safe_int(values, 4),
                'gps_lat': self._safe_float(values, 5),
                'gps_lon': self._safe_float(values, 6),
                'gps_alt': self._safe_float(values, 7),
                'ground_speed': self._safe_float(values, 8),
                'gps_time': self._safe_float(values, 9),
                'pressure': self._safe_float(values, 13),
                'temperature': self._safe_float(values, 14),
                'diff_pressure2': self._safe_float(values, 15),
                'sd_status': self._safe_bool(values, 16),
                'actuator_status': self._safe_bool(values, 17),
                'logging_active': self._safe_bool(values, 18),
                'write_rate': self._safe_int(values, 19),
                'space_left': self._safe_int(values, 20),
                'pix_boot_time_ms': self._safe_int(values, 22),
                'gps_bearing': self._safe_float(values, 29),
                'gps_bearing_magnetic': self._safe_float(values, 30),
                'photodiode_value1': self._safe_int(values, 35),
                'photodiode_value2': self._safe_int(values, 36),
                'fc_battery_voltage': self._safe_float(values, 37),
                'led_battery_voltage': self._safe_float(values, 38),
            }
            
            # Add derived fields
            data['gps_valid'] = data['gps_lat'] != 0.0 and data['gps_lon'] != 0.0
            data['altitude'] = data['gps_alt']
            data['led_status'] = data['photodiode_value1'] > 5 or data['photodiode_value2'] > 5
            
            return data
            
        except Exception as e:
            print(f"Error parsing FC packet: {e}")
            return None
    
    def _parse_gs_packet(self, packet_str, timestamp):
        """Parse Ground Station packet"""
        values = packet_str.split(',')
        
        try:
            data = {
                'timestamp': timestamp,
                'time_elapsed': (timestamp - self.start_time).total_seconds() if self.start_time else 0,
                'rssi': self._safe_int(values, 0),
                'snr': self._safe_int(values, 1),
                'frequency': self._safe_int(values, 2) if len(values) > 2 else 0,
            }
            return data
        except Exception as e:
            print(f"Error parsing GS packet: {e}")
            return None
    
    def _safe_int(self, values, idx, default=0):
        """Safely parse integer from values list"""
        try:
            return int(values[idx]) if idx < len(values) and values[idx].strip() else default
        except (ValueError, IndexError):
            return default
    
    def _safe_float(self, values, idx, default=0.0):
        """Safely parse float from values list"""
        try:
            return float(values[idx]) if idx < len(values) and values[idx].strip() else default
        except (ValueError, IndexError):
            return default
    
    def _safe_bool(self, values, idx, default=False):
        """Safely parse boolean from values list"""
        try:
            return bool(int(values[idx])) if idx < len(values) and values[idx].strip() else default
        except (ValueError, IndexError):
            return default
    
    def parse_event_log(self):
        """Parse the event log file"""
        if not self.event_log_path or not os.path.exists(self.event_log_path):
            print("Event log file not found or not specified")
            return None
            
        print("Parsing event log...")
        events = []
        
        with open(self.event_log_path, 'r') as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith('Event Log') or line.startswith('Started:') or line.startswith('---'):
                    continue
                
                # Parse event log entries
                event_match = re.match(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s+(.+)', line)
                if event_match:
                    timestamp_str = event_match.group(1)
                    event_description = event_match.group(2)
                    
                    try:
                        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                        events.append({
                            'timestamp': timestamp,
                            'event': event_description
                        })
                    except ValueError:
                        continue
        
        self.event_data = pd.DataFrame(events) if events else pd.DataFrame()
        print(f"Parsed {len(events)} events")
        
        return self.event_data
    
    def export_to_kml(self, output_file="flight_path.kml"):
        """Export GPS coordinates to KML file for Google Earth with special event markers only"""
        if self.flight_data is None or self.flight_data.empty:
            print("No flight data available for KML export")
            return False
            
        # Filter valid GPS coordinates
        valid_gps = self.flight_data[
            (self.flight_data['gps_valid'] == True) &
            (self.flight_data['gps_lat'] != 0) &
            (self.flight_data['gps_lon'] != 0)
        ].copy()
        
        if valid_gps.empty:
            print("No valid GPS coordinates found")
            return False
            
        # Detect special events
        termination_events = self.detect_termination_events()
        apogee_point = self.detect_apogee(valid_gps)
            
        print(f"Exporting special events from {len(valid_gps)} GPS points to KML...")
        print(f"Found {len(termination_events)} termination events and {'apogee' if apogee_point else 'no apogee'}")
        
        # Create KML structure
        kml = Element('kml')
        kml.set('xmlns', 'http://www.opengis.net/kml/2.2')
        
        document = SubElement(kml, 'Document')
        SubElement(document, 'name').text = 'Flight Events: Termination, De-termination, and Apogee'
        
        # Define styles for different marker types
        self._add_kml_styles(document)
        
        # Create placemark for the flight path (simplified)
        placemark = SubElement(document, 'Placemark')
        SubElement(placemark, 'name').text = 'Flight Path'
        SubElement(placemark, 'description').text = f'Flight path from {self.start_time}'
        
        # Style for the path (thinner, more subtle)
        style = SubElement(placemark, 'Style')
        line_style = SubElement(style, 'LineStyle')
        SubElement(line_style, 'color').text = '7f0000ff'  # Semi-transparent red line
        SubElement(line_style, 'width').text = '2'
        
        # Create LineString
        line_string = SubElement(placemark, 'LineString')
        SubElement(line_string, 'extrude').text = '1'
        SubElement(line_string, 'tessellate').text = '1'
        SubElement(line_string, 'altitudeMode').text = 'absolute'
        
        # Build coordinates string
        coordinates = []
        for _, row in valid_gps.iterrows():
            coordinates.append(f"{row['gps_lon']},{row['gps_lat']},{row['gps_alt']}")
        
        SubElement(line_string, 'coordinates').text = ' '.join(coordinates)
        
        # Add special event markers
        for event in termination_events:
            self._add_termination_marker(document, event)
        
        # Add apogee marker (balloon burst)
        if apogee_point:
            self._add_apogee_marker(document, apogee_point)
        
        # Write to file
        rough_string = tostring(kml, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        
        with open(output_file, 'w') as f:
            f.write(reparsed.toprettyxml(indent="  "))
            
        print(f"KML file with special events exported to: {output_file}")
        return True
    
    def plot_telemetry_data(self, output_dir="plots"):
        """Create plots of telemetry data over time"""
        if self.flight_data is None or self.flight_data.empty:
            print("No flight data available for plotting")
            return False
            
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Set up the plotting style
        plt.style.use('seaborn-v0_8' if 'seaborn-v0_8' in plt.style.available else 'default')
        
        # Plot 1: GPS Altitude, Ground Speed, Vertical Speed, and Total Speed
        fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(12, 16))
        
        valid_data = self.flight_data[self.flight_data['gps_valid'] == True]
        
        # Calculate vertical speed on the fly for valid data
        valid_data = valid_data.copy()
        valid_data['vertical_speed'] = 0.0
        
        for i in range(1, len(valid_data)):
            current_row = valid_data.iloc[i]
            previous_row = valid_data.iloc[i-1]
            
            time_diff = current_row['time_elapsed'] - previous_row['time_elapsed']
            if time_diff > 0:
                alt_diff = current_row['gps_alt'] - previous_row['gps_alt']
                valid_data.iloc[i, valid_data.columns.get_loc('vertical_speed')] = alt_diff / time_diff
        
        # Calculate total speed (magnitude of ground speed and vertical speed vector)
        valid_data['total_speed'] = np.sqrt(valid_data['ground_speed']**2 + valid_data['vertical_speed']**2)
        
        ax1.plot(valid_data['time_elapsed_minutes'], valid_data['gps_alt'], 'b-', linewidth=2, label='GPS Altitude')
        ax1.set_ylabel('Altitude (m)')
        ax1.set_title('Flight Altitude Over Time')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        ax2.plot(valid_data['time_elapsed_minutes'], valid_data['ground_speed'], 'g-', linewidth=2, label='Ground Speed')
        ax2.set_ylabel('Ground Speed (m/s)')
        ax2.set_title('Ground Speed Over Time')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        # Add vertical speed plot
        ax3.plot(valid_data['time_elapsed_minutes'], valid_data['vertical_speed'], 'r-', linewidth=2, label='Vertical Speed')
        ax3.axhline(y=0, color='k', linestyle='--', alpha=0.5)  # Reference line at 0
        ax3.set_ylabel('Vertical Speed (m/s)')
        ax3.set_title('Vertical Speed Over Time (Positive = Ascending, Negative = Descending)')
        ax3.grid(True, alpha=0.3)
        ax3.legend()
        
        # Add total speed plot (magnitude of horizontal and vertical velocity vector)
        ax4.plot(valid_data['time_elapsed_minutes'], valid_data['total_speed'], 'purple', linewidth=2, label='Total Speed')
        ax4.plot(valid_data['time_elapsed_minutes'], valid_data['ground_speed'], 'g--', linewidth=1, alpha=0.7, label='Ground Speed (reference)')
        ax4.plot(valid_data['time_elapsed_minutes'], np.abs(valid_data['vertical_speed']), 'r--', linewidth=1, alpha=0.7, label='|Vertical Speed| (reference)')
        ax4.set_ylabel('Total Speed (m/s)')
        ax4.set_xlabel('Time (minutes)')
        ax4.set_title('Total Speed Over Time (√(Ground Speed² + Vertical Speed²))')
        ax4.grid(True, alpha=0.3)
        ax4.legend()
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'altitude_speed.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        # Plot 2: Environmental Data
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 12))
        
        ax1.plot(self.flight_data['time_elapsed_minutes'], self.flight_data['temperature'], 'r-', linewidth=2)
        ax1.set_ylabel('Temperature (°C)')
        ax1.set_title('Temperature Over Time')
        ax1.grid(True, alpha=0.3)
        
        ax2.plot(self.flight_data['time_elapsed_minutes'], self.flight_data['pressure_kpa'], 'b-', linewidth=2)
        ax2.set_ylabel('Pressure (kPa)')
        ax2.set_title('Pressure Over Time')
        ax2.grid(True, alpha=0.3)
        
        ax3.plot(self.flight_data['time_elapsed_minutes'], self.flight_data['diff_pressure2_kpa'], 'g-', linewidth=2)
        ax3.set_ylabel('Differential Pressure (kPa)')
        ax3.set_xlabel('Time (minutes)')
        ax3.set_title('Differential Pressure Over Time')
        ax3.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'environmental_data.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        # Plot 3: Signal Strength
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        ax1.plot(self.flight_data['time_elapsed_minutes'], self.flight_data['rssi'], 'r-', linewidth=2, label='RSSI')
        ax1.set_ylabel('RSSI (dBm)')
        ax1.set_title('Signal Strength Over Time')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        ax2.plot(self.flight_data['time_elapsed_minutes'], self.flight_data['snr'], 'b-', linewidth=2, label='SNR')
        ax2.set_ylabel('SNR (dB)')
        ax2.set_xlabel('Time (minutes)')
        ax2.set_title('Signal-to-Noise Ratio Over Time')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'signal_strength.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        # Plot 4: System Status
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Battery voltages
        ax1.plot(self.flight_data['time_elapsed_minutes'], self.flight_data['fc_battery_voltage'], 'r-', linewidth=2, label='FC Battery')
        ax1.plot(self.flight_data['time_elapsed_minutes'], self.flight_data['led_battery_voltage'], 'b-', linewidth=2, label='LED Battery')
        ax1.set_ylabel('Voltage (V)')
        ax1.set_title('Battery Voltages Over Time')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Photodiode values
        ax2.plot(self.flight_data['time_elapsed_minutes'], self.flight_data['photodiode_value1'], 'g-', linewidth=2, label='Photodiode 1')
        ax2.plot(self.flight_data['time_elapsed_minutes'], self.flight_data['photodiode_value2'], 'orange', linewidth=2, label='Photodiode 2')
        ax2.set_ylabel('Photodiode Value')
        ax2.set_xlabel('Time (minutes)')
        ax2.set_title('Photodiode Values Over Time')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'system_status.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        # Plot 5: Flight Path Map
        if len(valid_data) > 0:
            fig, ax = plt.subplots(1, 1, figsize=(10, 8))
            
            # Create a scatter plot colored by altitude
            scatter = ax.scatter(valid_data['gps_lon'], valid_data['gps_lat'], 
                               c=valid_data['gps_alt'], cmap='viridis', s=20, alpha=0.7)
            
            # Add colorbar
            cbar = plt.colorbar(scatter, ax=ax)
            cbar.set_label('Altitude (m)')
            
            ax.set_xlabel('Longitude')
            ax.set_ylabel('Latitude')
            ax.set_title('Flight Path (colored by altitude)')
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'flight_path_map.png'), dpi=300, bbox_inches='tight')
            plt.close()
        
        # Plot 6: Actuator Status and Termination Events
        fig, ax = plt.subplots(1, 1, figsize=(12, 6))
        
        # Plot actuator status over time
        ax.plot(self.flight_data['time_elapsed_minutes'], self.flight_data['actuator_status'].astype(int), 
                'r-', linewidth=2, label='Actuator Status')
        
        # Mark termination events
        termination_events = self.detect_termination_events()
        for event in termination_events:
            color = 'red' if event['event_type'] == 'TERMINATION' else 'green'
            marker = '^' if event['event_type'] == 'TERMINATION' else 'v'
            ax.scatter(event['time_elapsed'] / 60.0, 1 if event['actuator_status'] else 0, 
                      c=color, marker=marker, s=100, 
                      label=f"{event['event_type']} ({event['timestamp'].strftime('%H:%M:%S')})")
        
        ax.set_ylabel('Actuator Status')
        ax.set_xlabel('Time (minutes)')
        ax.set_title('Actuator Status and Termination Events Over Time')
        ax.set_ylim(-0.1, 1.1)
        ax.set_yticks([0, 1])
        ax.set_yticklabels(['INACTIVE', 'ACTIVE'])
        ax.grid(True, alpha=0.3)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'actuator_status.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Plots saved to: {output_dir}")
        return True
    
    def create_event_timeline(self, output_file="event_timeline.png"):
        """Create a timeline visualization of events"""
        if self.event_data is None or self.event_data.empty:
            print("No event data available for timeline")
            return False
            
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Create y-positions for different event types
        event_types = {}
        y_pos = 0
        
        for _, row in self.event_data.iterrows():
            event_type = self._categorize_event(row['event'])
            if event_type not in event_types:
                event_types[event_type] = y_pos
                y_pos += 1
        
        # Plot events
        colors = plt.cm.Set3(np.linspace(0, 1, len(event_types)))
        
        for i, (_, row) in enumerate(self.event_data.iterrows()):
            event_type = self._categorize_event(row['event'])
            y = event_types[event_type]
            color = colors[list(event_types.keys()).index(event_type)]
            
            ax.scatter(row['timestamp'], y, c=[color], s=100, alpha=0.7)
            
            # Add event text
            ax.annotate(row['event'], (row['timestamp'], y), 
                       xytext=(5, 5), textcoords='offset points',
                       fontsize=8, ha='left', va='bottom',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
        
        # Set labels and title
        ax.set_xlabel('Time')
        ax.set_ylabel('Event Type')
        ax.set_title('Event Timeline')
        ax.set_yticks(list(event_types.values()))
        ax.set_yticklabels(list(event_types.keys()))
        
        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=5))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Event timeline saved to: {output_file}")
        return True
    
    def _categorize_event(self, event_description):
        """Categorize events based on description"""
        if 'sd_status' in event_description.lower():
            return 'SD Card Status'
        elif 'actuator_status' in event_description.lower():
            return 'Actuator Status'
        elif 'sent:' in event_description.lower():
            return 'Command Sent'
        elif 'logging' in event_description.lower():
            return 'Logging'
        else:
            return 'Other'
    
    def generate_summary_report(self, output_file="flight_summary.txt"):
        """Generate a comprehensive summary report"""
        if self.flight_data is None or self.flight_data.empty:
            print("No flight data available for summary")
            return False
            
        with open(output_file, 'w') as f:
            f.write("FLIGHT LOG ANALYSIS SUMMARY\n")
            f.write("="*50 + "\n\n")
            
            # Basic statistics
            f.write("BASIC STATISTICS\n")
            f.write("-" * 20 + "\n")
            f.write(f"Flight Duration: {self.flight_data['time_elapsed'].max():.2f} seconds ({self.flight_data['time_elapsed_minutes'].max():.2f} minutes)\n")
            f.write(f"Total FC Packets: {len(self.flight_data)}\n")
            f.write(f"Valid GPS Points: {len(self.flight_data[self.flight_data['gps_valid'] == True])}\n")
            f.write(f"Start Time: {self.start_time}\n\n")
            
            # Flight phases
            flight_phases = self.detect_flight_phases()
            if flight_phases:
                f.write("FLIGHT PHASES\n")
                f.write("-" * 20 + "\n")
                
                if 'release' in flight_phases:
                    release = flight_phases['release']
                    f.write(f"Balloon Release Time (UTC): {release['utc_time']}\n")
                    f.write(f"Release Altitude: {release['altitude']:.2f}m\n")
                    f.write(f"Release Location: ({release['gps_lat']:.6f}, {release['gps_lon']:.6f})\n\n")
                
                if 'apogee' in flight_phases:
                    apogee = flight_phases['apogee']
                    f.write(f"Apogee Time (UTC): {apogee['utc_time']}\n")
                    f.write(f"Apogee Altitude: {apogee['altitude']:.2f}m\n")
                    f.write(f"Apogee Location: ({apogee['gps_lat']:.6f}, {apogee['gps_lon']:.6f})\n\n")
                
                if 'landing' in flight_phases:
                    landing = flight_phases['landing']
                    f.write(f"Landing Time (UTC): {landing['utc_time']}\n")
                    f.write(f"Landing Altitude: {landing['altitude']:.2f}m\n")
                    f.write(f"Landing Location: ({landing['gps_lat']:.6f}, {landing['gps_lon']:.6f})\n\n")
                
                if 'durations' in flight_phases:
                    durations = flight_phases['durations']
                    f.write(f"Ascent Duration: {durations['ascent']:.2f} seconds ({durations['ascent']/60:.2f} minutes)\n")
                    f.write(f"Descent Duration: {durations['descent']:.2f} seconds ({durations['descent']/60:.2f} minutes)\n")
                    f.write(f"Total Flight Duration: {durations['total']:.2f} seconds ({durations['total']/60:.2f} minutes)\n\n")
            else:
                f.write("FLIGHT PHASES\n")
                f.write("-" * 20 + "\n")
                f.write("Unable to detect flight phases\n\n")
            
            # GPS statistics
            valid_gps = self.flight_data[self.flight_data['gps_valid'] == True]
            if len(valid_gps) > 0:
                # Calculate vertical speed for statistics
                valid_gps = valid_gps.copy()
                vertical_speeds = []
                total_speeds = []
                
                for i in range(1, len(valid_gps)):
                    current_row = valid_gps.iloc[i]
                    previous_row = valid_gps.iloc[i-1]
                    time_diff = current_row['time_elapsed'] - previous_row['time_elapsed']
                    if time_diff > 0:
                        alt_diff = current_row['gps_alt'] - previous_row['gps_alt']
                        vertical_speed = alt_diff / time_diff
                        vertical_speeds.append(vertical_speed)
                        
                        # Calculate total speed (magnitude of ground and vertical speed vector)
                        total_speed = np.sqrt(current_row['ground_speed']**2 + vertical_speed**2)
                        total_speeds.append(total_speed)
                
                f.write("GPS STATISTICS\n")
                f.write("-" * 20 + "\n")
                f.write(f"Max Altitude: {valid_gps['gps_alt'].max():.2f} m\n")
                f.write(f"Min Altitude: {valid_gps['gps_alt'].min():.2f} m\n")
                f.write(f"Max Ground Speed: {valid_gps['ground_speed'].max():.2f} m/s\n")
                f.write(f"Average Ground Speed: {valid_gps['ground_speed'].mean():.2f} m/s\n")
                
                if vertical_speeds:
                    f.write(f"Max Vertical Speed (Ascent): {max(vertical_speeds):.2f} m/s\n")
                    f.write(f"Max Vertical Speed (Descent): {min(vertical_speeds):.2f} m/s\n")
                    f.write(f"Average Vertical Speed: {sum(vertical_speeds)/len(vertical_speeds):.2f} m/s\n")
                
                if total_speeds:
                    f.write(f"Max Total Speed: {max(total_speeds):.2f} m/s\n")
                    f.write(f"Average Total Speed: {sum(total_speeds)/len(total_speeds):.2f} m/s\n")
                
                f.write(f"Latitude Range: {valid_gps['gps_lat'].min():.6f} to {valid_gps['gps_lat'].max():.6f}\n")
                f.write(f"Longitude Range: {valid_gps['gps_lon'].min():.6f} to {valid_gps['gps_lon'].max():.6f}\n\n")
            
            # Environmental statistics
            f.write("ENVIRONMENTAL STATISTICS\n")
            f.write("-" * 20 + "\n")
            f.write(f"Temperature Range: {self.flight_data['temperature'].min():.2f}°C to {self.flight_data['temperature'].max():.2f}°C\n")
            f.write(f"Pressure Range: {self.flight_data['pressure_kpa'].min():.2f} to {self.flight_data['pressure_kpa'].max():.2f} kPa\n")
            f.write(f"Average Temperature: {self.flight_data['temperature'].mean():.2f}°C\n")
            f.write(f"Average Pressure: {self.flight_data['pressure_kpa'].mean():.2f} kPa\n\n")
            
            # Signal statistics
            f.write("SIGNAL STATISTICS\n")
            f.write("-" * 20 + "\n")
            f.write(f"RSSI Range: {self.flight_data['rssi'].min()} to {self.flight_data['rssi'].max()} dBm\n")
            f.write(f"SNR Range: {self.flight_data['snr'].min()} to {self.flight_data['snr'].max()} dB\n")
            f.write(f"Average RSSI: {self.flight_data['rssi'].mean():.2f} dBm\n")
            f.write(f"Average SNR: {self.flight_data['snr'].mean():.2f} dB\n\n")
            
            # System status
            f.write("SYSTEM STATUS\n")
            f.write("-" * 20 + "\n")
            f.write(f"SD Card Status: {self.flight_data['sd_status'].sum()} true readings\n")
            f.write(f"Actuator Status: {self.flight_data['actuator_status'].sum()} true readings\n")
            f.write(f"LED Status: {self.flight_data['led_status'].sum()} true readings\n")
            f.write(f"Battery Voltage Range: {self.flight_data['fc_battery_voltage'].min():.2f}V to {self.flight_data['fc_battery_voltage'].max():.2f}V\n\n")
            
            # Termination events
            termination_events = self.detect_termination_events()
            if termination_events:
                f.write("TERMINATION EVENTS\n")
                f.write("-" * 20 + "\n")
                f.write(f"Total Termination Events: {len(termination_events)}\n")
                
                termination_count = len([e for e in termination_events if e['event_type'] == 'TERMINATION'])
                de_termination_count = len([e for e in termination_events if e['event_type'] == 'DE-TERMINATION'])
                
                f.write(f"Termination Events: {termination_count}\n")
                f.write(f"De-termination Events: {de_termination_count}\n\n")
                
                f.write("Event Details:\n")
                for i, event in enumerate(termination_events, 1):
                    f.write(f"  {i}. {event['event_type']} at {event['timestamp']}\n")
                    f.write(f"     Location: ({event['gps_lat']:.6f}, {event['gps_lon']:.6f})\n")
                    f.write(f"     Altitude: {event['gps_alt']:.2f}m\n")
                    f.write(f"     Time Elapsed: {event['time_elapsed']:.2f}s\n\n")
            else:
                f.write("TERMINATION EVENTS\n")
                f.write("-" * 20 + "\n")
                f.write("No termination events detected\n\n")
            
            # Event summary
            if self.event_data is not None and not self.event_data.empty:
                f.write("EVENT SUMMARY\n")
                f.write("-" * 20 + "\n")
                f.write(f"Total Events: {len(self.event_data)}\n")
                
                # Count event types
                event_counts = {}
                for _, row in self.event_data.iterrows():
                    event_type = self._categorize_event(row['event'])
                    event_counts[event_type] = event_counts.get(event_type, 0) + 1
                
                for event_type, count in event_counts.items():
                    f.write(f"{event_type}: {count} events\n")
        
        print(f"Summary report saved to: {output_file}")
        return True
    
    def detect_termination_events(self):
        """Detect termination and de-termination events from actuator status changes"""
        if self.flight_data is None or self.flight_data.empty:
            print("No flight data available for termination event detection")
            return []
        
        termination_events = []
        previous_actuator_status = None
        
        for _, row in self.flight_data.iterrows():
            current_actuator_status = row['actuator_status']
            
            # Check for state change
            if previous_actuator_status is not None and previous_actuator_status != current_actuator_status:
                event_type = "TERMINATION" if current_actuator_status else "DE-TERMINATION"
                
                # Only add if we have valid GPS coordinates
                if row['gps_valid'] and row['gps_lat'] != 0 and row['gps_lon'] != 0:
                    termination_events.append({
                        'timestamp': row['timestamp'],
                        'time_elapsed': row['time_elapsed'],
                        'event_type': event_type,
                        'actuator_status': current_actuator_status,
                        'gps_lat': row['gps_lat'],
                        'gps_lon': row['gps_lon'],
                        'gps_alt': row['gps_alt'],
                        'altitude': row['altitude'],
                        'temperature': row['temperature'],
                        'pressure': row['pressure'],
                        'ground_speed': row['ground_speed'],
                        'rssi': row['rssi'],
                        'snr': row['snr']
                    })
                    
                    print(f"Detected {event_type} event at {row['timestamp']} - GPS: ({row['gps_lat']:.6f}, {row['gps_lon']:.6f})")
            
            previous_actuator_status = current_actuator_status
        
        print(f"Found {len(termination_events)} termination events")
        return termination_events

    def detect_apogee(self, valid_gps_data):
        """Detect apogee (maximum altitude) point - balloon burst location"""
        if valid_gps_data.empty:
            return None
        
        # Find the point with maximum altitude
        max_alt_idx = valid_gps_data['gps_alt'].idxmax()
        apogee_point = valid_gps_data.loc[max_alt_idx]
        
        print(f"Detected apogee at {apogee_point['timestamp']} - "
              f"GPS: ({apogee_point['gps_lat']:.6f}, {apogee_point['gps_lon']:.6f}), "
              f"Altitude: {apogee_point['gps_alt']:.2f}m")
        
        return {
            'timestamp': apogee_point['timestamp'],
            'time_elapsed': apogee_point['time_elapsed'],
            'gps_lat': apogee_point['gps_lat'],
            'gps_lon': apogee_point['gps_lon'],
            'gps_alt': apogee_point['gps_alt'],
            'altitude': apogee_point['altitude'],
            'temperature': apogee_point['temperature'],
            'pressure': apogee_point['pressure'],
            'ground_speed': apogee_point['ground_speed'],
            'rssi': apogee_point['rssi'],
            'snr': apogee_point['snr']
        }
    
    def _add_kml_styles(self, document):
        """Add KML styles for different marker types"""
        
        # Style for termination events (red star)
        termination_style = SubElement(document, 'Style')
        termination_style.set('id', 'termination_style')
        icon_style = SubElement(termination_style, 'IconStyle')
        SubElement(icon_style, 'scale').text = '1.5'
        SubElement(icon_style, 'color').text = 'ff0000ff'  # Red
        icon = SubElement(icon_style, 'Icon')
        SubElement(icon, 'href').text = 'http://maps.google.com/mapfiles/kml/shapes/star.png'
        
        # Style for de-termination events (green star)
        de_termination_style = SubElement(document, 'Style')
        de_termination_style.set('id', 'de_termination_style')
        icon_style = SubElement(de_termination_style, 'IconStyle')
        SubElement(icon_style, 'scale').text = '1.5'
        SubElement(icon_style, 'color').text = 'ff00ff00'  # Green
        icon = SubElement(icon_style, 'Icon')
        SubElement(icon, 'href').text = 'http://maps.google.com/mapfiles/kml/shapes/star.png'
        
        # Style for apogee/balloon burst (orange explosion)
        apogee_style = SubElement(document, 'Style')
        apogee_style.set('id', 'apogee_style')
        icon_style = SubElement(apogee_style, 'IconStyle')
        SubElement(icon_style, 'scale').text = '2.0'
        SubElement(icon_style, 'color').text = 'ff0080ff'  # Orange
        icon = SubElement(icon_style, 'Icon')
        SubElement(icon, 'href').text = 'http://maps.google.com/mapfiles/kml/shapes/explosion.png'
    
    def _add_termination_marker(self, document, event):
        """Add a termination event marker to the KML document"""
        
        placemark = SubElement(document, 'Placemark')
        SubElement(placemark, 'name').text = f"{event['event_type']} Event"
        
        # Create detailed description
        description = (
            f"<b>{event['event_type']} EVENT</b><br/><br/>"
            f"<b>Time:</b> {event['timestamp']}<br/>"
            f"<b>Time Elapsed:</b> {event['time_elapsed']:.2f} seconds<br/>"
            f"<b>Actuator Status:</b> {'ACTIVE' if event['actuator_status'] else 'INACTIVE'}<br/><br/>"
            f"<b>Location:</b><br/>"
            f"Latitude: {event['gps_lat']:.6f}<br/>"
            f"Longitude: {event['gps_lon']:.6f}<br/>"
            f"Altitude: {event['gps_alt']:.2f}m<br/><br/>"
            f"<b>Telemetry Data:</b><br/>"
            f"Ground Speed: {event['ground_speed']:.2f}m/s<br/>"
            f"Temperature: {event['temperature']:.2f}°C<br/>"
            f"Pressure: {event['pressure']:.2f}Pa<br/>"
            f"RSSI: {event['rssi']}dBm<br/>"
            f"SNR: {event['snr']}dB"
        )
        
        SubElement(placemark, 'description').text = description
        
        # Apply appropriate style
        style_url = SubElement(placemark, 'styleUrl')
        if event['event_type'] == 'TERMINATION':
            style_url.text = '#termination_style'
        else:
            style_url.text = '#de_termination_style'
        
        # Create point
        point = SubElement(placemark, 'Point')
        SubElement(point, 'extrude').text = '1'
        SubElement(point, 'altitudeMode').text = 'absolute'
        SubElement(point, 'coordinates').text = f"{event['gps_lon']},{event['gps_lat']},{event['gps_alt']}"
    
    def _add_apogee_marker(self, document, apogee_event):
        """Add an apogee (balloon burst) marker to the KML document"""
        
        placemark = SubElement(document, 'Placemark')
        SubElement(placemark, 'name').text = "APOGEE - Balloon Burst"
        
        # Create detailed description
        description = (
            f"<b>APOGEE - BALLOON BURST</b><br/><br/>"
            f"<b>Time:</b> {apogee_event['timestamp']}<br/>"
            f"<b>Time Elapsed:</b> {apogee_event['time_elapsed']:.2f} seconds<br/>"
            f"<b>Maximum Altitude:</b> {apogee_event['gps_alt']:.2f}m<br/><br/>"
            f"<b>Location:</b><br/>"
            f"Latitude: {apogee_event['gps_lat']:.6f}<br/>"
            f"Longitude: {apogee_event['gps_lon']:.6f}<br/><br/>"
            f"<b>Telemetry Data at Apogee:</b><br/>"
            f"Ground Speed: {apogee_event['ground_speed']:.2f}m/s<br/>"
            f"Temperature: {apogee_event['temperature']:.2f}°C<br/>"
            f"Pressure: {apogee_event['pressure']:.2f}Pa<br/>"
            f"RSSI: {apogee_event['rssi']}dBm<br/>"
            f"SNR: {apogee_event['snr']}dB"
        )
        
        SubElement(placemark, 'description').text = description
        
        # Use apogee style
        SubElement(placemark, 'styleUrl').text = '#apogee_style'
        
        # Add point
        point = SubElement(placemark, 'Point')
        SubElement(point, 'coordinates').text = f"{apogee_event['gps_lon']},{apogee_event['gps_lat']},{apogee_event['gps_alt']}"

    def run_full_analysis(self, output_dir="analysis_output"):
        """Run the complete analysis pipeline"""
        print("Starting full flight log analysis...")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Parse data
        self.parse_flight_log()
        self.convert_units()  # Convert units after parsing
        self.parse_event_log()
        
        # Generate outputs
        self.export_to_kml(os.path.join(output_dir, "flight_path.kml"))
        self.plot_telemetry_data(os.path.join(output_dir, "plots"))
        self.create_event_timeline(os.path.join(output_dir, "event_timeline.png"))
        self.generate_summary_report(os.path.join(output_dir, "flight_summary.txt"))
        
        print(f"Analysis complete! Results saved to: {output_dir}")
    
    def _calculate_vertical_speed(self):
        """Calculate vertical speed from rate of change of altitude"""
        if self.flight_data.empty:
            return
        
        # Filter valid GPS data for calculation
        valid_gps = self.flight_data[self.flight_data['gps_valid'] == True].copy()
        
        if len(valid_gps) < 2:
            # Not enough data points for calculation
            self.flight_data['vertical_speed'] = 0.0
            return
        
        # Sort by time to ensure proper order
        valid_gps = valid_gps.sort_values('time_elapsed')
        
        # Calculate vertical speed using difference method
        vertical_speeds = []
        
        for i in range(len(valid_gps)):
            if i == 0:
                # First point: use forward difference
                if len(valid_gps) > 1:
                    dt = valid_gps.iloc[1]['time_elapsed'] - valid_gps.iloc[0]['time_elapsed']
                    dalt = valid_gps.iloc[1]['gps_alt'] - valid_gps.iloc[0]['gps_alt']
                    if dt > 0:
                        vertical_speed = dalt / dt
                    else:
                        vertical_speed = 0.0
                else:
                    vertical_speed = 0.0
            elif i == len(valid_gps) - 1:
                # Last point: use backward difference
                dt = valid_gps.iloc[i]['time_elapsed'] - valid_gps.iloc[i-1]['time_elapsed']
                dalt = valid_gps.iloc[i]['gps_alt'] - valid_gps.iloc[i-1]['gps_alt']
                if dt > 0:
                    vertical_speed = dalt / dt
                else:
                    vertical_speed = 0.0
            else:
                # Middle points: use central difference (more accurate)
                dt = valid_gps.iloc[i+1]['time_elapsed'] - valid_gps.iloc[i-1]['time_elapsed']
                dalt = valid_gps.iloc[i+1]['gps_alt'] - valid_gps.iloc[i-1]['gps_alt']
                if dt > 0:
                    vertical_speed = dalt / dt
                else:
                    vertical_speed = 0.0
            
            vertical_speeds.append(vertical_speed)
        
        # Create a mapping from index to vertical speed
        valid_gps['vertical_speed'] = vertical_speeds
        
        # Apply smoothing to reduce noise (simple moving average)
        window_size = 5
        if len(valid_gps) >= window_size:
            valid_gps['vertical_speed'] = valid_gps['vertical_speed'].rolling(
                window=window_size, center=True, min_periods=1
            ).mean()
        
        # Map vertical speeds back to the full dataset
        # Initialize all vertical speeds to 0
        self.flight_data['vertical_speed'] = 0.0
        
        # Update vertical speeds for valid GPS points
        for idx, row in valid_gps.iterrows():
            self.flight_data.at[idx, 'vertical_speed'] = row['vertical_speed']
        
        print(f"Calculated vertical speed for {len(valid_gps)} valid GPS points")
        print(f"Vertical speed range: {valid_gps['vertical_speed'].min():.2f} to {valid_gps['vertical_speed'].max():.2f} m/s")
    
    def convert_units(self):
        """Convert units for better display in plots and reports"""
        if self.flight_data is None or self.flight_data.empty:
            return
            
        # Convert time to minutes for all plots
        self.flight_data['time_elapsed_minutes'] = self.flight_data['time_elapsed'] / 60.0
        
        # Convert pressure to kPa for all plots
        self.flight_data['pressure_kpa'] = self.flight_data['pressure'] / 1000.0
        self.flight_data['diff_pressure2_kpa'] = self.flight_data['diff_pressure2'] / 1000.0

    def detect_flight_phases(self):
        """Detect key flight phases: release, apogee, and landing"""
        if self.flight_data is None or self.flight_data.empty:
            return None
            
        valid_gps = self.flight_data[
            (self.flight_data['gps_valid'] == True) &
            (self.flight_data['gps_lat'] != 0) &
            (self.flight_data['gps_lon'] != 0)
        ].copy()
        
        if valid_gps.empty:
            return None
            
        phases = {}
        
        # Find balloon release (start of significant ascent)
        # Look for sustained positive vertical speed above a threshold
        ascent_threshold = 2.0  # m/s sustained ascent
        min_ascent_duration = 60  # seconds
        
        release_point = None
        for i in range(len(valid_gps) - 10):  # Check 10 points ahead
            current_row = valid_gps.iloc[i]
            
            # Check if we have sustained ascent for the next several points
            future_points = valid_gps.iloc[i:i+10]
            if len(future_points) >= 10:
                avg_vertical_speed = future_points['vertical_speed'].mean()
                if avg_vertical_speed > ascent_threshold:
                    release_point = current_row
                    break
        
        if release_point is not None:
            phases['release'] = {
                'timestamp': release_point['timestamp'],
                'utc_time': release_point['timestamp'],
                'time_elapsed': release_point['time_elapsed'],
                'altitude': release_point['gps_alt'],
                'gps_lat': release_point['gps_lat'],
                'gps_lon': release_point['gps_lon'],
                'vertical_speed': release_point['vertical_speed']
            }
        
        # Find apogee (highest altitude point)
        max_alt_idx = valid_gps['gps_alt'].idxmax()
        apogee_row = valid_gps.loc[max_alt_idx]
        
        phases['apogee'] = {
            'timestamp': apogee_row['timestamp'],
            'utc_time': apogee_row['timestamp'],
            'time_elapsed': apogee_row['time_elapsed'],
            'altitude': apogee_row['gps_alt'],
            'gps_lat': apogee_row['gps_lat'],
            'gps_lon': apogee_row['gps_lon'],
            'vertical_speed': apogee_row['vertical_speed']
        }
        
        # Find landing (end of significant descent)
        # Look for when vertical speed approaches zero and stays low
        landing_threshold = 1.0  # m/s vertical speed threshold
        min_stable_duration = 120  # seconds of stable flight
        
        landing_point = None
        # Start looking from the last 1/4 of the flight
        start_idx = len(valid_gps) * 3 // 4
        
        for i in range(start_idx, len(valid_gps) - 10):
            current_row = valid_gps.iloc[i]
            
            # Check if we have stable low vertical speed for the next several points
            future_points = valid_gps.iloc[i:i+10]
            if len(future_points) >= 10:
                max_abs_vertical_speed = future_points['vertical_speed'].abs().max()
                if max_abs_vertical_speed < landing_threshold:
                    landing_point = current_row
                    break
        
        # If no stable landing detected, use the last point
        if landing_point is None:
            landing_point = valid_gps.iloc[-1]
        
        phases['landing'] = {
            'timestamp': landing_point['timestamp'],
            'utc_time': landing_point['timestamp'],
            'time_elapsed': landing_point['time_elapsed'],
            'altitude': landing_point['gps_alt'],
            'gps_lat': landing_point['gps_lat'],
            'gps_lon': landing_point['gps_lon'],
            'vertical_speed': landing_point['vertical_speed']
        }
        
        # Calculate flight duration phases
        if 'release' in phases:
            ascent_duration = phases['apogee']['time_elapsed'] - phases['release']['time_elapsed']
            descent_duration = phases['landing']['time_elapsed'] - phases['apogee']['time_elapsed']
            total_duration = phases['landing']['time_elapsed'] - phases['release']['time_elapsed']
            
            phases['durations'] = {
                'ascent': ascent_duration,
                'descent': descent_duration,
                'total': total_duration
            }
        
        return phases

def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description='Analyze flight log data')
    parser.add_argument('log_file', help='Path to the flight log file')
    parser.add_argument('--event-log', help='Path to the event log file')
    parser.add_argument('--output-dir', default='analysis_output', help='Output directory')
    
    args = parser.parse_args()
    
    # Create analyzer and run analysis
    analyzer = FlightLogAnalyzer(args.log_file, args.event_log)
    analyzer.run_full_analysis(args.output_dir)


if __name__ == "__main__":
    main()
