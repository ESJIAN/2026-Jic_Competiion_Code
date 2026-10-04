
import sys
import time
import serial
from rplidar import RPLidar, RPLidarException

def test_lidar_robust(port, baudrate):
    print(f"Testing {port} at {baudrate} (Robust)...")
    try:
        # First, try to stop the lidar using raw serial
        ser = serial.Serial(port, baudrate, timeout=1)
        ser.write(b'\xa5\x25') # STOP command
        time.sleep(0.5)
        ser.flushInput()
        ser.close()
        
        # Now use the library
        lidar = RPLidar(port, baudrate=baudrate, timeout=3)
        # The library might have already started the motor, let's stop it just in case
        lidar.stop()
        lidar.clear_input()
        
        info = lidar.get_info()
        print(f"Success! Info: {info}")
        return True
    except Exception as e:
        print(f"Failed: {e}")
        return False
    finally:
        pass

if __name__ == "__main__":
    port = "/dev/ttyS1"
    for baud in [115200, 256000]:
        if test_lidar_robust(port, baud):
            print(f"Working configuration: {port} at {baud}")
            sys.exit(0)
    print("No working configuration found.")
