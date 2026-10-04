"""
M2 Motor (Left Rear) and M4 Servo Test Script.

This script tests the functionality of the M2 motor (Left Rear) and M4 servo using I2C communication.
It performs the following operations:
1. Reads battery voltage.
2. Configures motor parameters.
3. Reads encoder values.
4. Controls motor/servo using PWM and speed modes.

Usage:
    python3 tests/chassis/right_motor.py
"""

import sys
import time
import struct
import yaml
from pathlib import Path

from smbus2 import SMBus

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from program.src.support.logger import get_logger
from program.src.support.config_loader import load_chassis_config

logger = get_logger(__name__)

# Load configuration
config = load_chassis_config()
i2c_conf = config.get('i2c_config', {})
motor_conf = config.get('motor_config', {})
reg_conf = config.get('register_config', {})

# I2C Configuration
BUS_NUM = i2c_conf.get('bus_num', 5)
DEVICE_ADDR = i2c_conf.get('device_addr', 0x26)

# Register Addresses
REG_MOTOR_TYPE = reg_conf.get('REG_MOTOR_TYPE', 0x01)
REG_DEADZONE = reg_conf.get('REG_DEADZONE', 0x02)
REG_MAGNETIC_LINES = reg_conf.get('REG_MAGNETIC_LINES', 0x03)
REG_REDUCTION_RATIO = reg_conf.get('REG_REDUCTION_RATIO', 0x04)
REG_WHEEL_DIAMETER = reg_conf.get('REG_WHEEL_DIAMETER', 0x05)
REG_SPEED_CONTROL = reg_conf.get('REG_SPEED_CONTROL', 0x06)
REG_PWM_CONTROL = reg_conf.get('REG_PWM_CONTROL', 0x07)
REG_BATTERY_VOLTAGE = reg_conf.get('REG_BATTERY_VOLTAGE', 0x08)
REG_M2_ENCODER = reg_conf.get('REG_M2_ENCODER', 0x12)
REG_M4_ENCODER = reg_conf.get('REG_M4_ENCODER', 0x16)

def read_battery_voltage(bus):
    """
    Read the battery voltage.

    Args:
        bus (SMBus): The I2C bus object.

    Returns:
        float: Battery voltage in Volts, or None if failed.
    """
    try:
        data = bus.read_i2c_block_data(DEVICE_ADDR, REG_BATTERY_VOLTAGE, 2)
        if len(data) >= 2:
            voltage = ((data[0] << 8) | data[1]) / 10.0
            logger.info(f"[Status] Battery Voltage: {voltage:.2f} V")
            return voltage
        else:
            logger.error("[Error] Failed to read battery voltage: Insufficient data length")
            return None
    except OSError as e:
        logger.error(f"[Error] Failed to read battery voltage: {e}")
        return None

def read_m2_encoder(bus):
    """
    Read the M2 motor encoder value.

    Args:
        bus (SMBus): The I2C bus object.

    Returns:
        int: Encoder value, or None if failed.
    """
    try:
        data = bus.read_i2c_block_data(DEVICE_ADDR, REG_M2_ENCODER, 2)
        if len(data) >= 2:
            encoder_value = (data[0] << 8 | data[1])
            if encoder_value & 0x8000:
                encoder_value = encoder_value - 0x10000
            logger.info(f"[Status] M2 Encoder Pulse Value: {encoder_value}")
            return encoder_value
        else:
            logger.error("[Error] Failed to read M2 encoder: Insufficient data length")
            return None
    except OSError as e:
        logger.error(f"[Error] Failed to read M2 encoder: {e}")
        return None

def set_m2_pwm(bus, pwm_value):
    """
    Set the PWM value for M2 motor.

    Args:
        bus (SMBus): The I2C bus object.
        pwm_value (int): PWM value (-3600 to 3600).

    Returns:
        bool: True if successful, False otherwise.
    """
    if pwm_value > 3600:
        pwm_value = 3600
    elif pwm_value < -3600:
        pwm_value = -3600
    
    pwm_int = int(pwm_value)
    data_bytes = bytearray()
    data_bytes.extend(struct.pack('>h', 0))       # M1
    data_bytes.extend(struct.pack('>h', pwm_int)) # M2
    data_bytes.extend(struct.pack('>h', 0))       # M3
    data_bytes.extend(struct.pack('>h', 0))       # M4
    
    try:
        bus.write_i2c_block_data(DEVICE_ADDR, REG_PWM_CONTROL, list(data_bytes))
        logger.info(f"Set M2 PWM value: {pwm_value}")
        return True
    except OSError as e:
        logger.error(f"I2C write failed: {e}")
        return False

def set_m2_speed(bus, speed_value):
    """
    Set the speed value for M2 motor.

    Args:
        bus (SMBus): The I2C bus object.
        speed_value (int): Speed value (-1000 to 1000).

    Returns:
        bool: True if successful, False otherwise.
    """
    if speed_value > 1000:
        speed_value = 1000
        logger.warning(f"[Warning] Speed value out of range, limited to: {speed_value}")
    elif speed_value < -1000:
        speed_value = -1000
        logger.warning(f"[Warning] Speed value out of range, limited to: {speed_value}")
    
    data_bytes = bytearray()
    data_bytes.extend(struct.pack('>h', 0))         # M1
    data_bytes.extend(struct.pack('>h', int(speed_value))) # M2
    data_bytes.extend(struct.pack('>h', 0))         # M3
    data_bytes.extend(struct.pack('>h', 0))         # M4
    
    try:
        bus.write_i2c_block_data(DEVICE_ADDR, REG_SPEED_CONTROL, list(data_bytes))
        logger.info(f"[Control] Set M2 speed value: {speed_value}")
        return True
    except OSError as e:
        logger.error(f"[Error] I2C write failed: {e}")
        return False

def config_m2_motor(bus):
    """
    Configure M2 motor parameters.

    Args:
        bus (SMBus): The I2C bus object.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        logger.info("\n=== Configure M2 Motor Parameters ===")
        motor_type = motor_conf.get('motor_type', 1)
        logger.info(f"1. Configure motor type: {motor_type}")
        bus.write_byte_data(DEVICE_ADDR, REG_MOTOR_TYPE, motor_type)
        time.sleep(0.1)
        
        deadzone_value = motor_conf.get('deadzone', 1600)
        logger.info(f"2. Configure deadzone: {deadzone_value}")
        deadzone_data = struct.pack('>h', deadzone_value)
        bus.write_i2c_block_data(DEVICE_ADDR, REG_DEADZONE, list(deadzone_data))
        time.sleep(0.1)
        
        magnetic_lines = motor_conf.get('magnetic_lines', 11)
        logger.info(f"3. Configure magnetic lines: {magnetic_lines}")
        magnetic_data = struct.pack('>H', magnetic_lines)
        bus.write_i2c_block_data(DEVICE_ADDR, REG_MAGNETIC_LINES, list(magnetic_data))
        time.sleep(0.1)
        
        reduction_ratio = motor_conf.get('reduction_ratio', 30)
        logger.info(f"4. Configure reduction ratio: {reduction_ratio}")
        reduction_data = struct.pack('>H', reduction_ratio)
        bus.write_i2c_block_data(DEVICE_ADDR, REG_REDUCTION_RATIO, list(reduction_data))
        time.sleep(0.1)
        
        logger.info("[Done] M2 Motor configuration completed!")
        return True
    except OSError as e:
        logger.error(f"[Error] M2 Motor configuration failed: {e}")
        return False

def read_m4_servo_position(bus):
    """
    Read M4 servo position.

    Args:
        bus (SMBus): The I2C bus object.

    Returns:
        int: Servo position value, or None if failed.
    """
    try:
        data = bus.read_i2c_block_data(DEVICE_ADDR, REG_M4_ENCODER, 2)
        if len(data) >= 2:
            position_value = (data[0] << 8 | data[1])
            if position_value & 0x8000:
                position_value = position_value - 0x10000
            logger.info(f"M4 Servo Position: {position_value}")
            return position_value
        else:
            logger.error("Failed to read M4 servo position: Insufficient data length")
            return None
    except OSError as e:
        logger.error(f"Failed to read M4 servo position: {e}")
        return None

def set_m4_servo_speed(bus, speed_value):
    """
    Set M4 servo speed (control).

    Args:
        bus (SMBus): The I2C bus object.
        speed_value (int): Speed value (-500 to 500).

    Returns:
        bool: True if successful, False otherwise.
    """
    if speed_value > 500:
        speed_value = 500
    elif speed_value < -500:
        speed_value = -500
    
    speed_int = int(speed_value)
    data_bytes = bytearray()
    data_bytes.extend(struct.pack('>h', 0))
    data_bytes.extend(struct.pack('>h', 0))
    data_bytes.extend(struct.pack('>h', 0))
    data_bytes.extend(struct.pack('>h', speed_int)) # M4
    
    try:
        bus.write_i2c_block_data(DEVICE_ADDR, REG_SPEED_CONTROL, list(data_bytes))
        logger.info(f"Set M4 servo speed: {speed_value}")
        return True
    except OSError as e:
        logger.error(f"I2C write failed: {e}")
        return False

def config_m4_servo(bus):
    """
    Configure M4 servo parameters.

    Args:
        bus (SMBus): The I2C bus object.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        logger.info("\n=== Configure M4 Servo Parameters ===")
        logger.info("1. Configure M4 as servo type...")
        bus.write_byte_data(DEVICE_ADDR, REG_MOTOR_TYPE, 4)  # Servo type fixed to 4
        time.sleep(0.5)
        
        logger.info("2. Configure servo deadzone to 100...")
        deadzone_data = struct.pack('>h', 100)
        bus.write_i2c_block_data(DEVICE_ADDR, REG_DEADZONE, list(deadzone_data))
        time.sleep(0.5)
        
        logger.info("Servo configuration completed!")
        return True
    except OSError as e:
        logger.error(f"Servo configuration failed: {e}")
        return False

def main():
    """Main function to run the M2 motor and M4 servo test."""
    logger.info(f"Opening I2C Bus {BUS_NUM}...")
    try:
        bus = SMBus(BUS_NUM)
    except Exception as e:
        logger.error(f"Failed to open bus: {e}")
        return

    logger.info("Starting test: Sending 4-channel motor driver protocol commands to address 0x26...")
    logger.info("Test Scope: M2 Motor (Left Rear) and M4 Servo (Steering)")
    
    try:
        logger.info("=== M2 Motor Test Start ===")
        
        # 1. Read Battery Voltage
        logger.info("\n1. Reading Battery Voltage...")
        voltage = read_battery_voltage(bus)
        if voltage is None:
            logger.warning("Warning: Failed to read battery voltage, continuing test...")
        
        # 2. Read M2 Encoder Data
        logger.info("\n2. Reading M2 Encoder Initial Data...")
        initial_encoder = read_m2_encoder(bus)
        
        # 3. Configure M2 Motor Parameters
        logger.info("\n3. Configuring M2 Motor Parameters (Optional)...")
        config_m2_motor(bus)
        
        # 4. PWM Control Test - Forward Rotation
        logger.info("\n4. PWM Control Test - M2 Forward Rotation")
        logger.info("   Expected: M2 Motor (Left Rear) rotates forward")
        if set_m2_pwm(bus, 1000):
            logger.info("   PWM control sent successfully, motor should start rotating")
            time.sleep(3)
        else:
            logger.error("   PWM control failed")
        
        # 5. Read Encoder Data Change
        logger.info("\n5. Reading M2 Encoder Data (Rotating)...")
        read_m2_encoder(bus)
        
        # 6. Stop Motor
        logger.info("\n6. Stopping M2 Motor...")
        set_m2_pwm(bus, 0)
        logger.info("   Motor should stop rotating")
        time.sleep(2)
        
        # 9. Read Final Encoder Data
        logger.info("\n9. Reading M2 Encoder Final Data...")
        final_encoder = read_m2_encoder(bus)
        
        # 10. Try Speed Control
        logger.info("\n10. Speed Control Test (Only valid for motors with encoders)...")
        if set_m2_speed(bus, 300):
            logger.info("   Speed control sent successfully. If motor has encoder, it will run at speed 300")
            time.sleep(2)
            
            logger.info("   Reading M2 Encoder Data (Speed Control)...")
            read_m2_encoder(bus)
            
            set_m2_speed(bus, 0)
            logger.info("   Speed control stopped")
        else:
            logger.error("   Speed control failed")
        
        # 11. Final Stop All Motors
        logger.info("\n11. Ensuring All Motors Stop...")
        try:
            bus.write_i2c_block_data(DEVICE_ADDR, REG_PWM_CONTROL, [0, 0, 0, 0, 0, 0, 0, 0])
            logger.info("   All motors stopped")
        except OSError as e:
            logger.error(f"Failed to stop motors: {e}")
        
        logger.info("\n=== M2 Motor Test End ===")
        logger.info("Test Summary:")
        logger.info(f"- Battery Voltage: {voltage if voltage else 'Read Failed'}")
        logger.info(f"- M2 Encoder Initial: {initial_encoder}")
        logger.info(f"- M2 Encoder Final: {final_encoder}")
        
    except KeyboardInterrupt:
        logger.warning("\nEmergency Stop All Motors...")
        try:
            bus.write_i2c_block_data(DEVICE_ADDR, REG_PWM_CONTROL, [0, 0, 0, 0, 0, 0, 0, 0])
        except:
            pass
        logger.warning("All motors stopped")
    except Exception as e:
        logger.error(f"Exception occurred during test: {e}")
    finally:
        try:
            bus.close()
        except:
            pass

if __name__ == "__main__":
    main()
