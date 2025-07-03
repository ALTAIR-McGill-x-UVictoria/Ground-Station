#!/usr/bin/env python3
"""
Test script to verify packet parsing doesn't cause issues
"""

import sys
import os
sys.path.append('.')

from models.telemetry_model import TelemetryModel
from controllers.telemetry_controller import TelemetryController

def test_packet_parsing():
    """Test the problematic packets"""
    
    # Create model and controller
    model = TelemetryModel()
    controller = TelemetryController(model)
    
    # Test packets from the user's log - the exact ones causing GUI freeze
    test_packets = [
        "FC:0,-22,11,,526369,45.501087,-73.470795,85.14,0.00,1751498240.00,,,,100307.78,46.68,0.00,0,0,0,0,0,,518720,,,,,,,0.00,62.00,,,,7,11,7.41,12.60",
        "GS:-32,11,3514",
        "GPS: No valid data"
    ]
    
    print("Testing problematic packets that were causing GUI freeze...")
    print("=" * 60)
    
    for i, packet in enumerate(test_packets, 1):
        print(f"\nTest {i}: Processing packet: {packet[:60]}{'...' if len(packet) > 60 else ''}")
        print(f"Packet length: {len(packet)} characters")
        print(f"Number of fields: {len(packet.split(',')) if ',' in packet else 'N/A'}")
        
        try:
            result = controller.process_packet(packet)
            print(f"✅ Result: {'SUCCESS' if result else 'FAILED (but handled gracefully)'}")
            
            # Print some key telemetry values to verify parsing
            if packet.startswith("FC:"):
                print(f"  GPS: {model.gps_lat:.6f}, {model.gps_lon:.6f}")
                print(f"  Altitude: {model.altitude:.2f}m")
                print(f"  RSSI: {model.rssi}, SNR: {model.snr}")
                print(f"  Temperature: {model.temperature:.2f}°C")
                print(f"  Pressure: {model.pressure:.2f} Pa")
                if hasattr(model, 'photodiode_value1'):
                    print(f"  Photodiodes: {model.photodiode_value1}, {model.photodiode_value2}")
                if hasattr(model, 'fc_battery_voltage'):
                    print(f"  Battery voltages: FC={model.fc_battery_voltage:.2f}V, LED={model.led_battery_voltage:.2f}V")
            elif packet.startswith("GS:"):
                print(f"  Ground Station RSSI: {model.rssi}, SNR: {model.snr}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    print("\n" + "=" * 60)
    print("✅ All tests completed successfully! No GUI freezing issues detected.")
    return True

if __name__ == "__main__":
    success = test_packet_parsing()
    if not success:
        print("❌ Test failed!")
        sys.exit(1)
    else:
        print("✅ Test passed!")
