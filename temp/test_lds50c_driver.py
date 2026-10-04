import sys
from pathlib import Path
import time

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.support.driver.lidar_driver import LDS50CDriver

def test_lds50c():
    port = "/dev/ttyS1"
    baudrate = 500000
    
    driver = LDS50CDriver(port, baudrate)
    if driver.connect():
        print("Connected to LDS-50C. Waiting for scans...")
        try:
            scan_count = 0
            for scan in driver.iter_scans():
                scan_count += 1
                print(f"Received scan {scan_count} with {len(scan)} points.")
                if scan_count >= 5:
                    break
        except Exception as e:
            print(f"Error during scanning: {e}")
        finally:
            driver.disconnect()
    else:
        print("Failed to connect.")

if __name__ == "__main__":
    test_lds50c()
