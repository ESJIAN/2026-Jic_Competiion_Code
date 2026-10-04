import time
import math
import random
import serial
import threading
import struct
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT))
from program.src.support.logger import get_logger

class LidarDriver:
    """Mock Lidar Driver for testing."""
    def __init__(self):
        self.connected = True
        self.lidar_type = "Mock (LDS-50C compatible)"
        
    def get_scan(self):
        """
        Return mock LiDAR scan data.
        Returns a list of ranges in meters for 360 degrees.
        """
        ranges = []
        for angle in range(360):
            rad = math.radians(angle)
            c = math.cos(rad)
            s = math.sin(rad)
            
            dist_x = 2.5 / abs(c) if abs(c) > 1e-3 else 100.0
            dist_y = 2.5 / abs(s) if abs(s) > 1e-3 else 100.0
            
            dist = min(dist_x, dist_y)
            dist += random.uniform(-0.05, 0.05)
            ranges.append(dist)
            
        return {
            "timestamp": time.time(),
            "ranges": ranges,
            "angle_min": 0,
            "angle_max": 2 * math.pi,
            "angle_increment": 2 * math.pi / 360,
            "range_min": 0.1,
            "range_max": 12.0
        }

class LDS50CDriver:
    """Driver for LDS-50C LiDAR."""
    def __init__(self, port, baudrate=500000, timeout=1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.logger = get_logger('lds50c_driver')
        self.running = False
        self.lock = threading.Lock()
        
    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            self.running = True
            self.logger.info(f"Connected to LDS-50C on {self.port} at {self.baudrate}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to LDS-50C: {e}")
            return False
            
    def disconnect(self):
        self.running = False
        if self.ser:
            self.ser.close()
            self.ser = None
        self.logger.info("Disconnected from LDS-50C")

    def iter_scans(self, **kwargs):
        """Mock RPLidar's iter_scans behavior."""
        buffer = b""
        current_full_scan = []
        last_angle = 0
        
        while self.running:
            try:
                if self.ser.in_waiting > 0:
                    data = self.ser.read(self.ser.in_waiting)
                    buffer += data
                    
                    while len(buffer) >= 6:
                        header_idx = -1
                        has_sector_angle = False
                        for i in range(len(buffer) - 1):
                            if buffer[i] == 0xCE and buffer[i+1] == 0xFA:
                                header_idx = i
                                has_sector_angle = False
                                break
                            if buffer[i] == 0xCF and buffer[i+1] == 0xFA:
                                header_idx = i
                                has_sector_angle = True
                                break
                        
                        if header_idx == -1:
                            buffer = buffer[-1:]
                            break
                        
                        if header_idx > 0:
                            buffer = buffer[header_idx:]
                        
                        if len(buffer) < 6:
                            break
                            
                        n_points = struct.unpack('<H', buffer[2:4])[0]
                        start_angle_raw = struct.unpack('<H', buffer[4:6])[0]
                        
                        header_size = 6
                        if has_sector_angle:
                            header_size += 2
                            if len(buffer) < header_size:
                                break
                        
                        packet_size = header_size + n_points * 3 + 2
                        if len(buffer) < packet_size:
                            break
                            
                        packet = buffer[:packet_size]
                        buffer = buffer[packet_size:]
                        
                        # Checksum
                        received_checksum = struct.unpack('<H', packet[-2:])[0]
                        calculated_checksum = sum(packet[:-2]) & 0xFFFF
                        if calculated_checksum != received_checksum:
                            # self.logger.warning(f"Checksum mismatch")
                            pass
                        
                        start_angle = start_angle_raw / 10.0
                        data_offset = header_size
                        
                        for i in range(n_points):
                            intensity = packet[data_offset]
                            distance = struct.unpack('<H', packet[data_offset+1:data_offset+3])[0]
                            
                            angle = (start_angle + i * 0.1) % 360 
                            
                            if angle < last_angle:
                                if current_full_scan:
                                    yield current_full_scan
                                    current_full_scan = []
                            
                            current_full_scan.append((intensity, angle, distance))
                            last_angle = angle
                            data_offset += 3
                else:
                    time.sleep(0.005)
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error in iter_scans: {e}")
                time.sleep(0.1)

    def get_info(self):
        return "LDS-50C Lidar"
        
    def get_health(self):
        return ("Good", 0)
        
    def stop(self):
        self.disconnect()
        
    def stop_motor(self):
        pass
        
    def clear_input(self):
        if self.ser:
            self.ser.reset_input_buffer()

if __name__ == "__main__":

    logger = get_logger("LidarDriver")
    logger.info("Testing LidarDriver")



    
