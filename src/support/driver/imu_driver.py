import time
import adafruit_bno055
from adafruit_extended_bus import ExtendedI2C as I2C
from program.src.support.logger import get_logger
from program.src.support.config_loader import load_imu_config

logger = get_logger(__name__)

class IMUDriver:
    def __init__(self, bus_num=None, address=None):
        """
        Initialize the BNO055 IMU driver.
        
        Args:
            bus_num (int): I2C bus number. If None, loaded from config.
            address (int): I2C address of the sensor. If None, loaded from config.
        """
        config = load_imu_config()
        i2c_config = config.get('i2c_config', {})
        
        self.bus_num = bus_num if bus_num is not None else i2c_config.get('bus_num', 5)
        self.address = address if address is not None else i2c_config.get('device_addr', 0x29)
        
        self.connected = False
        self.sensor = None
        
        try:
            # Use ExtendedI2C for specific bus number
            self.i2c = I2C(self.bus_num)
            # Initialize BNO055
            self.sensor = adafruit_bno055.BNO055_I2C(self.i2c, address=self.address)
            self.connected = True
            logger.info(f"IMU BNO055 initialized on Bus {self.bus_num} Address {hex(self.address)}")
        except Exception as e:
            logger.error(f"Failed to initialize IMU BNO055 on Bus {self.bus_num}: {e}")
            self.connected = False

    def get_data(self):
        """
        Return IMU data.
        
        Returns:
            dict: Dictionary containing timestamp, orientation, angular_velocity, and linear_acceleration.
                  Returns None if sensor is not connected or read fails.
        """
        if not self.connected or not self.sensor:
            # Try to reconnect? For now, just return None
            return None

        try:
            # Orientation (Quaternion): (w, x, y, z)
            quat = self.sensor.quaternion
            
            # Angular Velocity (Gyro): (x, y, z)
            # Units: rad/s (standard for CircuitPython libraries)
            gyro = self.sensor.gyro
            
            # Acceleration (including gravity): (x, y, z) in m/s^2
            # Matches the mock behavior which had z ~ 9.8
            accel = self.sensor.acceleration
            
            # Calibration status: (sys, gyro, accel, mag)
            calibration = self.sensor.calibration_status
            
            # Handle potential None returns from sensor (e.g. if I2C error occurs momentarily)
            if quat is None: quat = (1.0, 0.0, 0.0, 0.0)
            if gyro is None: gyro = (0.0, 0.0, 0.0)
            if accel is None: accel = (0.0, 0.0, 0.0)
            if calibration is None: calibration = (0, 0, 0, 0)

            return {
                "timestamp": time.time(),
                "calibration": {
                    "sys": calibration[0],
                    "gyro": calibration[1],
                    "accel": calibration[2],
                    "mag": calibration[3]
                },
                "orientation": {
                    "x": quat[1],
                    "y": quat[2],
                    "z": quat[3],
                    "w": quat[0]
                },
                "angular_velocity": {
                    "x": gyro[0],
                    "y": gyro[1],
                    "z": gyro[2]
                },
                "linear_acceleration": {
                    "x": accel[0],
                    "y": accel[1],
                    "z": accel[2]
                }
            }
        except Exception as e:
            logger.error(f"Error reading IMU data: {e}")
            return None

