import sys
import os
import time
import logging

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.insert(0, PROJECT_ROOT)

from program.src.support.driver.chassis_driver import ChassisDriver
from program.src.support.driver.imu_driver import IMUDriver

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ChassisTest")

class ChassisTest:
    def __init__(self):
        try:
            self.driver = ChassisDriver()
            logger.info("ChassisDriver initialized successfully.")
            logger.info(f"Config: Wheel Diameter={self.driver.wheel_diameter_mm}mm, Reduction={self.driver.reduction_ratio}, Lines={self.driver.magnetic_lines}")
        except Exception as e:
            logger.error(f"Failed to initialize ChassisDriver: {e}")
            sys.exit(1)
            
        try:
            self.imu = IMUDriver()
            logger.info("IMUDriver initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize IMUDriver: {e}")
            self.imu = None

    def _monitor_speed(self, duration=2.0, interval=0.5):
        """
        Helper to monitor and log speed and encoder values for a duration.
        """
        start_time = time.time()
        steps = 0
        
        # Simple velocity integration vars
        vx_imu = 0.0
        last_imu_time = start_time

        while time.time() - start_time < duration:
            current_time = time.time()
            dt = current_time - last_imu_time
            last_imu_time = current_time

            # Read speed from Chassis
            v_left, v_right = self.driver.wheel_speed()
            
            # Read raw encoder values (accessing internal protected member for debug)
            enc_left = self.driver._last_encoders.get(self.driver.left_motor_id, 0)
            enc_right = self.driver._last_encoders.get(self.driver.right_motor_id, 0)
            
            # Read IMU
            imu_info = "IMU: N/A"
            if self.imu:
                imu_data = self.imu.get_data()
                if imu_data:
                    # Angular Velocity Z (rad/s)
                    gyro_z = imu_data['angular_velocity']['z']
                    
                    # Linear Acceleration X (m/s^2) - assuming X is forward
                    accel_x = imu_data['linear_acceleration']['x']
                    
                    # Simple Integration for Linear Velocity (prone to drift, but good for short test)
                    # Note: sensor.acceleration includes gravity. We'd ideally want linear_acceleration (no gravity).
                    # Assuming the driver returns raw acceleration, we might see offsets.
                    vx_imu += accel_x * dt
                    
                    imu_info = f"IMU: Wz={gyro_z:.3f} rad/s, Ax={accel_x:.2f} m/s², Vx(est)={vx_imu:.2f} m/s"
            
            logger.info(f"  [Status] Speed: L={v_left:.3f}m/s, R={v_right:.3f}m/s | Enc: L={enc_left}, R={enc_right} | {imu_info}")
            
            time.sleep(interval)
            steps += 1

    def test_motor_rotate(self):
        """
        Test individual motors to verify wiring and mapping.
        """
        logger.info(">>> TEST: Individual Motor Rotation")
        
        # Test Left Motor
        logger.info("  -> Testing LEFT Motor (Forward) for 2 seconds...")
        speeds = [0, 0, 0, 0]
        # Assuming left_motor_id is 1-based index
        if 1 <= self.driver.left_motor_id <= 4:
            # Set a moderate speed/pwm
            speeds[self.driver.left_motor_id - 1] = 200 * self.driver.left_motor_dir
        
        self.driver._set_motors_speed(speeds)
        self._monitor_speed(duration=2.0)
        self.driver.stop()
        time.sleep(0.5)

        # Test Right Motor
        logger.info("  -> Testing RIGHT Motor (Forward) for 2 seconds...")
        speeds = [0, 0, 0, 0]
        if 1 <= self.driver.right_motor_id <= 4:
            speeds[self.driver.right_motor_id - 1] = 200 * self.driver.right_motor_dir
        
        self.driver._set_motors_speed(speeds)
        self._monitor_speed(duration=2.0)
        self.driver.stop()
        logger.info("  -> Motor Test Complete\n")

    def test_chassis_translate(self):
        """
        Test linear movement (Forward/Backward) with encoder feedback.
        """
        logger.info(">>> TEST: Chassis Translation (Linear)")
        
        # Forward
        target_v = 0.2
        logger.info(f"  -> Moving FORWARD at {target_v} m/s for 2 seconds...")
        self.driver.move(target_v)
        self._monitor_speed(duration=2.0)
        self.driver.stop()
        time.sleep(1.0)

        # Backward
        target_v = -0.2
        logger.info(f"  -> Moving BACKWARD at {target_v} m/s for 2 seconds...")
        self.driver.move(target_v)
        self._monitor_speed(duration=2.0)
        self.driver.stop()
        logger.info("  -> Translation Test Complete\n")

    def test_chassis_rotate(self):
        """
        Test rotation (CW/CCW) with encoder feedback.
        """
        logger.info(">>> TEST: Chassis Rotation")
        
        # CCW (Left)
        target_w = 1.0
        logger.info(f"  -> Rotating CCW (Left) at {target_w} rad/s for 2 seconds...")
        self.driver.rotate(target_w)
        self._monitor_speed(duration=2.0)
        self.driver.stop()
        time.sleep(1.0)

        # CW (Right)
        target_w = -1.0
        logger.info(f"  -> Rotating CW (Right) at {target_w} rad/s for 2 seconds...")
        self.driver.rotate(target_w)
        self._monitor_speed(duration=2.0)
        self.driver.stop()
        logger.info("  -> Rotation Test Complete\n")

    def run_all(self):
        try:
            logger.info("Starting Chassis Test Suite...")
            
            # 1. Check Battery
            voltage = self.driver.battery_voltage()
            logger.info(f"Current Battery Voltage: {voltage:.2f} V")
            if voltage < 9.0:
                logger.warning("Battery voltage might be too low!")

            # 2. Run Tests
            self.test_motor_rotate()
            time.sleep(1)
            
            self.test_chassis_translate()
            time.sleep(1)
            
            self.test_chassis_rotate()
            
            logger.info("All tests finished successfully.")
            
        except KeyboardInterrupt:
            logger.warning("Test interrupted by user.")
        except Exception as e:
            logger.error(f"Test failed with error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            logger.info("Stopping all motors...")
            self.driver.stop()
            self.driver.close()

if __name__ == "__main__":
    test = ChassisTest()
    test.run_all()
