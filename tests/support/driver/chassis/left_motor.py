"""
M3 Motor (Right Front) Rotation Test Script.

This script tests the functionality of the M3 motor (Right Front) using I2C communication.
It performs the following operations:
1. Reads battery voltage.
2. Configures motor parameters (type, deadzone, magnetic lines, reduction ratio).
3. Reads M3 encoder values.
4. Controls M3 motor using PWM.
5. Controls M3 motor using speed (closed-loop).

Usage:
    python3 tests/chassis/left_motor.py
"""

import struct
import sys
import time
from pathlib import Path

import yaml
from smbus2 import SMBus

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parents[2]))

from program.src.support.logger import get_logger

logger = get_logger(__name__)


def load_config():
    """
    Load configuration from chasis_params.yaml.

    Returns:
        dict: Configuration dictionary.
    """
    config_path = Path(__file__).parents[2] / 'config/chasis_params.yaml'
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {}


# Load configuration
config = load_config()
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
REG_M3_ENCODER = reg_conf.get('REG_M3_ENCODER', 0x14)


def read_battery_voltage(bus):
    """
    Read the battery voltage from the driver board.

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


def read_m3_encoder(bus):
    """
    Read the M3 encoder value.

    Args:
        bus (SMBus): The I2C bus object.

    Returns:
        int: Encoder value (ticks), or None if failed.
    """
    try:
        data = bus.read_i2c_block_data(DEVICE_ADDR, REG_M3_ENCODER, 2)
        if len(data) >= 2:
            encoder_value = (data[0] << 8 | data[1])
            # Handle signed 16-bit integer
            if encoder_value & 0x8000:
                encoder_value = encoder_value - 0x10000
            logger.info(f"[Status] M3 Encoder Value: {encoder_value}")
            return encoder_value
        else:
            logger.error("[Error] Failed to read M3 encoder: Insufficient data length")
            return None
    except OSError as e:
        logger.error(f"[Error] Failed to read M3 encoder: {e}")
        return None


def set_m3_pwm(bus, pwm_value):
    """
    Set the PWM value for the M3 motor.

    Args:
        bus (SMBus): The I2C bus object.
        pwm_value (int): PWM value (-3600 to 3600).

    Returns:
        bool: True if successful, False otherwise.
    """
    if pwm_value > 3600:
        pwm_value = 3600
        logger.warning(f"[Warning] PWM value limited to: {pwm_value}")
    elif pwm_value < -3600:
        pwm_value = -3600
        logger.warning(f"[Warning] PWM value limited to: {pwm_value}")

    # Prepare data: [M1_H, M1_L, M2_H, M2_L, M3_H, M3_L, M4_H, M4_L]
    data_bytes = bytearray()
    data_bytes.extend(struct.pack('>h', 0))          # M1
    data_bytes.extend(struct.pack('>h', 0))          # M2
    data_bytes.extend(struct.pack('>h', int(pwm_value)))  # M3
    data_bytes.extend(struct.pack('>h', 0))          # M4

    try:
        bus.write_i2c_block_data(DEVICE_ADDR, REG_PWM_CONTROL, list(data_bytes))
        logger.info(f"[Control] Set M3 PWM: {pwm_value}")
        return True
    except OSError as e:
        logger.error(f"[Error] I2C Write Failed (PWM): {e}")
        return False


def set_m3_speed(bus, speed_value):
    """
    Set the target speed for the M3 motor (Closed-loop control).

    Args:
        bus (SMBus): The I2C bus object.
        speed_value (int): Target speed (-1000 to 1000).

    Returns:
        bool: True if successful, False otherwise.
    """
    if speed_value > 1000:
        speed_value = 1000
        logger.warning(f"[Warning] Speed value limited to: {speed_value}")
    elif speed_value < -1000:
        speed_value = -1000
        logger.warning(f"[Warning] Speed value limited to: {speed_value}")

    data_bytes = bytearray()
    data_bytes.extend(struct.pack('>h', 0))            # M1
    data_bytes.extend(struct.pack('>h', 0))            # M2
    data_bytes.extend(struct.pack('>h', int(speed_value)))  # M3
    data_bytes.extend(struct.pack('>h', 0))            # M4

    try:
        bus.write_i2c_block_data(DEVICE_ADDR, REG_SPEED_CONTROL, list(data_bytes))
        logger.info(f"[Control] Set M3 Speed: {speed_value}")
        return True
    except OSError as e:
        logger.error(f"[Error] I2C Write Failed (Speed): {e}")
        return False


def config_motor_params(bus):
    """
    Configure global motor parameters.

    Args:
        bus (SMBus): The I2C bus object.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        logger.info("=== Configuring Motor Parameters ===")
        
        motor_type = motor_conf.get('motor_type', 1)
        logger.info(f"1. Motor Type: {motor_type}")
        bus.write_byte_data(DEVICE_ADDR, REG_MOTOR_TYPE, motor_type)
        time.sleep(0.1)

        deadzone_value = motor_conf.get('deadzone', 1600)
        logger.info(f"2. Deadzone: {deadzone_value}")
        deadzone_data = struct.pack('>h', deadzone_value)
        bus.write_i2c_block_data(DEVICE_ADDR, REG_DEADZONE, list(deadzone_data))
        time.sleep(0.1)

        magnetic_lines = motor_conf.get('magnetic_lines', 11)
        logger.info(f"3. Magnetic Lines: {magnetic_lines}")
        magnetic_data = struct.pack('>H', magnetic_lines)
        bus.write_i2c_block_data(DEVICE_ADDR, REG_MAGNETIC_LINES, list(magnetic_data))
        time.sleep(0.1)

        reduction_ratio = motor_conf.get('reduction_ratio', 30)
        logger.info(f"4. Reduction Ratio: {reduction_ratio}")
        reduction_data = struct.pack('>H', reduction_ratio)
        bus.write_i2c_block_data(DEVICE_ADDR, REG_REDUCTION_RATIO, list(reduction_data))
        time.sleep(0.1)

        logger.info("[Success] Motor parameters configured.")
        return True
    except OSError as e:
        logger.error(f"[Error] Failed to configure motor parameters: {e}")
        return False


def main():
    """Main function to run the M3 motor test."""
    logger.info(f"Opening I2C Bus {BUS_NUM}...")
    try:
        bus = SMBus(BUS_NUM)
    except Exception as e:
        logger.error(f"Failed to open I2C bus: {e}")
        return

    logger.info("Starting M3 Motor Test...")
    logger.info("Target: M3 Motor (Right Front)")

    try:
        # 1. Read Battery Voltage
        logger.info("\n[Step 1] Reading Battery Voltage...")
        voltage = read_battery_voltage(bus)
        if voltage is not None and voltage < 6.0:
            logger.warning(f"[Warning] Low battery voltage: {voltage:.2f}V")

        # 2. Configure Motor Parameters
        config_motor_params(bus)

        # 3. Read Initial Encoder Value
        logger.info("\n[Step 2] Reading Initial M3 Encoder Value...")
        initial_encoder = read_m3_encoder(bus)

        # 4. PWM Control Test (Forward)
        logger.info("\n[Step 3] PWM Test - M3 Forward")
        if set_m3_pwm(bus, 1500):
            time.sleep(3)
            read_m3_encoder(bus)

        # 5. PWM Control Test (Backward)
        logger.info("\n[Step 4] PWM Test - M3 Backward")
        if set_m3_pwm(bus, -1500):
            time.sleep(3)
            read_m3_encoder(bus)

        # 6. Stop Motor (PWM)
        logger.info("\n[Step 5] Stop M3 Motor (PWM=0)...")
        set_m3_pwm(bus, 0)
        time.sleep(1)

        # 7. Speed Control Test (Forward)
        logger.info("\n[Step 6] Speed Control Test - M3 Forward")
        if set_m3_speed(bus, 400):
            time.sleep(3)
            read_m3_encoder(bus)

        # 8. Speed Control Test (Backward)
        logger.info("\n[Step 7] Speed Control Test - M3 Backward")
        if set_m3_speed(bus, -400):
            time.sleep(3)
            read_m3_encoder(bus)

        # 9. Stop Motor (Speed)
        logger.info("\n[Step 8] Stop M3 Motor (Speed=0)...")
        set_m3_speed(bus, 0)
        time.sleep(1)

        # 10. Final Encoder Value
        logger.info("\n[Step 9] Reading Final M3 Encoder Value...")
        final_encoder = read_m3_encoder(bus)
        if initial_encoder is not None and final_encoder is not None:
            logger.info(f"Encoder Delta: {final_encoder - initial_encoder}")

        logger.info("\n" + "=" * 50)
        logger.info("M3 Motor Test Completed!")
        logger.info("=" * 50)

    except KeyboardInterrupt:
        logger.warning("\n[User Interrupt] Stopping motor...")
        set_m3_pwm(bus, 0)
        set_m3_speed(bus, 0)
    except Exception as e:
        logger.error(f"\n[Exception] Error during test: {e}")
    finally:
        try:
            set_m3_pwm(bus, 0)
            set_m3_speed(bus, 0)
            bus.close()
            logger.info("[Cleanup] I2C bus closed, motor stopped.")
        except Exception:
            pass


if __name__ == "__main__":
    main()
