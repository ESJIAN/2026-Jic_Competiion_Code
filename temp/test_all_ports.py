
import sys
import time
from rplidar import RPLidar, RPLidarException

def test_lidar(port, baudrate):
    print(f"Testing {port} at {baudrate}...")
    lidar = None
    try:
        lidar = RPLidar(port, baudrate=baudrate, timeout=3)
        info = lidar.get_info()
        print(f"Success! Info: {info}")
        health = lidar.get_health()
        print(f"Health: {health}")
        return True
    except Exception as e:
        print(f"Failed: {e}")
        return False
    finally:
        if lidar:
            lidar.disconnect()

if __name__ == "__main__":
    for port in ["/dev/ttyS1", "/dev/ttyS5"]:
        for baud in [115200, 256000]:
            if test_lidar(port, baud):
                print(f"Working: {port} at {baud}")
                sys.exit(0)
    print("No working configuration found.")
