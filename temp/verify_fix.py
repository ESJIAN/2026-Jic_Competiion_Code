import serial
import time
import sys
from rplidar import RPLidar

def force_stop_lidar(port, baudrate):
    print(f"Attempting to force stop Lidar on {port}...")
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        ser.write(b'\xa5\x25')
        time.sleep(0.5)
        ser.close()
        print("Force stop command sent.")
    except Exception as e:
        print(f"Could not force stop: {e}")

def test_connection(port, baudrate):
    force_stop_lidar(port, baudrate)
    
    print(f"Connecting to RPLidar on {port} at {baudrate}...")
    lidar = None
    try:
        lidar = RPLidar(port, baudrate=baudrate, timeout=3)
        info = lidar.get_info()
        print(f"SUCCESS! Info: {info}")
        health = lidar.get_health()
        print(f"Health: {health}")
        return True
    except Exception as e:
        print(f"FAILED to connect: {e}")
        if "Incorrect descriptor starting bytes" in str(e):
            print("Suggestion: This confirms the baudrate might still be wrong or the device is busy.")
        return False
    finally:
        if lidar:
            lidar.disconnect()

if __name__ == "__main__":
    for port in ["/dev/ttyS1", "/dev/ttyS5"]:
        print(f"\n{'='*10} Testing Port: {port} {'='*10}")
        # Test common baudrates
        for baud in [921600, 500000, 460800, 256000, 115200]:
            print("-" * 30)
            if test_connection(port, baud):
                print(f"Verified working at {baud}!")
                sys.exit(0)
            time.sleep(1)
