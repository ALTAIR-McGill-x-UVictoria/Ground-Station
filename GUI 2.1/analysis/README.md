# Flight Log Analysis Tools

This directory contains tools for analyzing flight log data from the HAB Ground Station.

## Features

- **GPS Export**: Export GPS coordinates to KML format for viewing in Google Earth
- **Telemetry Plotting**: Generate comprehensive plots of all telemetry data over time
- **Event Timeline**: Create visual timeline of system events
- **Summary Reports**: Generate detailed statistical summaries

## Files

- `flight_log_analyzer.py`: Main analysis class with all functionality
- `run_analysis.py`: Simple script to run analysis on specific files
- `requirements.txt`: Python package dependencies
- `README.md`: This file

## Installation

1. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Quick Analysis
Run the pre-configured analysis script:
```bash
python run_analysis.py
```

This will analyze:
- Flight log: `../logs/flight_log_2025-07-03_22-10-39.txt`
- Event log: `../event_logs/event_log_2025-07-03_22-07-27.txt`

### Custom Analysis
Use the analyzer directly for custom analysis:
```bash
python flight_log_analyzer.py path/to/flight_log.txt --event-log path/to/event_log.txt --output-dir custom_output
```

### Using as a Python Module
```python
from flight_log_analyzer import FlightLogAnalyzer

# Create analyzer
analyzer = FlightLogAnalyzer("path/to/flight_log.txt", "path/to/event_log.txt")

# Run full analysis
analyzer.run_full_analysis("output_directory")

# Or run individual components
analyzer.parse_flight_log()
analyzer.export_to_kml("flight_path.kml")
analyzer.plot_telemetry_data("plots")
analyzer.create_event_timeline("timeline.png")
analyzer.generate_summary_report("summary.txt")
```

## Output Files

### Google Earth KML
- `flight_path.kml`: 3D flight path with altitude information
- Waypoints every 50 data points with telemetry information

### Plots
- `altitude_speed.png`: GPS altitude and ground speed over time
- `environmental_data.png`: Temperature, pressure, and differential pressure
- `signal_strength.png`: RSSI and SNR over time
- `system_status.png`: Battery voltages and photodiode readings
- `flight_path_map.png`: 2D map view of flight path colored by altitude

### Event Timeline
- `event_timeline.png`: Visual timeline of all system events

### Summary Report
- `flight_summary.txt`: Comprehensive statistical summary including:
  - Flight duration and packet counts
  - GPS statistics (max/min altitude, speed ranges)
  - Environmental statistics (temperature, pressure ranges)
  - Signal statistics (RSSI, SNR ranges)
  - System status summaries
  - Event counts by category

## Data Structure

The analyzer processes FC (Flight Computer) packets according to the structure defined in `telemetry_controller.py`:

- Basic data: RSSI, SNR, timestamps
- GPS data: Latitude, longitude, altitude, ground speed
- Environmental: Temperature, pressure, differential pressure
- System status: SD card, actuator, logging status
- Power: Battery voltages
- Sensors: Photodiode readings

## Event Categories

Events are automatically categorized:
- **SD Card Status**: SD card operations
- **Actuator Status**: Actuator state changes
- **Command Sent**: Commands sent to the system
- **Logging**: Logging operations
- **Other**: Miscellaneous events

## Requirements

- Python 3.7+
- pandas
- matplotlib
- numpy
- seaborn

## Notes

- The analyzer handles missing or invalid data gracefully
- GPS coordinates are validated before export
- All plots are saved as high-resolution PNG files
- KML files include altitude information for 3D visualization in Google Earth
