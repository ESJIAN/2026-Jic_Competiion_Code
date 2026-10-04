
import sys
import time
import threading
from pathlib import Path

# Mocking rplidar for the purpose of "familiarization" without hardware
# In a real scenario, this would be: from rplidar import RPLidar, RPLidarException
try:
    from rplidar import RPLidar, RPLidarException
    MOCK_MODE = False
except ImportError:
    print("RPLidar library not found. Running in MOCK mode for API demonstration.")
    MOCK_MODE = True
    
    class RPLidarException(Exception):
        pass

    class RPLidar:
        def __init__(self, port, baudrate=115200, timeout=1):
            self.port = port
            print(f"[SDK] Initializing RPLidar on {port} at {baudrate} baud")
            
        def stop(self):
            print("[SDK] Stopping scanning")
            
        def stop_motor(self):
            print("[SDK] Stopping motor")
            
        def start_motor(self):
            print("[SDK] Starting motor")
            
        def disconnect(self):
            print("[SDK] Disconnecting")
            
        def iter_scans(self, max_buf_meas=500):
            print("[SDK] Starting scan iteration...")
            # Yield fake data: (quality, angle, distance_mm)
            for i in range(10):
                time.sleep(0.1)
                # Simulate a partial scan
                scan_data = []
                for angle in range(0, 360, 10):
                    scan_data.append((15, angle, 1000 + angle)) # 1m + angle mm
                yield scan_data

def run_lidar_demo():
    """
    Demonstrates how to use the RPLidar SDK to fetch and process scan data.
    """
    PORT_NAME = '/dev/ttyUSB0'
    
    lidar = RPLidar(PORT_NAME, baudrate=115200, timeout=1)

    try:
        print("--- Starting Lidar Demo ---")
        lidar.start_motor()
        
        # iter_scans yields a list of tuples (quality, angle, distance)
        # Note: 'scan' is NOT a full 360 scan, but a chunk of measurements.
        # The SDK tries to group them, but we should handle partials if needed.
        for i, scan in enumerate(lidar.iter_scans()):
            print(f"Scan batch {i+1}: got {len(scan)} points")
            
            # Example processing:
            for (_, angle, distance) in scan:
                if 0 <= angle < 5: # Check points right in front
                    print(f"  Front obstacle at {angle:.1f}°: {distance:.1f}mm")
            
            if i >= 5: # Stop after 5 batches for demo
                break
                
    except RPLidarException as e:
        print(f"Lidar error: {e}")
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        lidar.stop()
        lidar.stop_motor()
        lidar.disconnect()
        print("--- Lidar Demo Finished ---")

if __name__ == "__main__":
    run_lidar_demo()
