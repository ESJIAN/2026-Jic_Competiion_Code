"""
Chassis Rotation and Motor Integration Test Script.

This script performs a comprehensive test of the chassis motion capabilities:
1. Individual Motor Tests:
   - Calls `left_motor.py` to test M3 motor (Right Front).
   - Calls `right_motor.py` to test M2 motor (Left Rear).
2. Chassis Rotation Test:
   - Tests simultaneous differential rotation (spin in place) using `ChassisDriver`.
     - Clockwise (Left Forward, Right Backward)
     - Counter-Clockwise (Left Backward, Right Forward)

Usage:
    python3 tests/chassis/chassis_rotate.py
"""

import sys
import time
import importlib
import yaml
from pathlib import Path

from program.src.support.logger import get_logger
from program.src.support.driver.chassis_driver import ChassisDriver

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
# Add current directory to sys.path to allow importing sibling scripts
sys.path.insert(0, str(Path(__file__).parent))

logger = get_logger(__name__)

# Load configuration
CONFIG_PATH = PROJECT_ROOT / 'config/chasis_params.yaml'

def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r') as f:
            return yaml.safe_load(f)
    return {}

# Import sibling motor test scripts
try:
    import program.tests.support.driver.chassis.left_motor as left_motor
    import program.tests.support.driver.chassis.right_motor as right_motor
except ImportError as e:
    print(f"Error importing motor scripts: {e}")
    sys.exit(1)


def test_individual_wheels():
    """
    Execute individual motor test scripts.
    """
    logger.info("\n" + "="*50)
    logger.info("PHASE 1: Individual Wheel Tests")
    logger.info("="*50)

    # Test Left Motor (M3 - Right Front based on script name/content mapping)
    # Note: left_motor.py actually controls M3 (Right Front) per its docstring, 
    # but we follow the file naming convention requested.
    logger.info("\n>>> Running Left Motor Test Script (left_motor.py)...")
    try:
        left_motor.main()
        logger.info(">>> Left Motor Test Completed Successfully.")
    except Exception as e:
        logger.error(f">>> Left Motor Test Failed: {e}")

    time.sleep(1)

    # Test Right Motor (M2 - Left Rear based on script name/content mapping)
    logger.info("\n>>> Running Right Motor Test Script (right_motor.py)...")
    try:
        right_motor.main()
        logger.info(">>> Right Motor Test Completed Successfully.")
    except Exception as e:
        logger.error(f">>> Right Motor Test Failed: {e}")
    
    time.sleep(1)

def test_chassis_rotation():
    """
    Execute chassis differential rotation tests using ChassisDriver.
    """
    logger.info("\n" + "="*50)
    logger.info("PHASE 2: Chassis Simultaneous Rotation Test")
    logger.info("="*50)

    logger.info("Initializing Chassis Driver...")
    try:
        config = load_chassis_config()
        driver = ChassisDriver()
        # Update motor mapping: M2=Left, M3=Right (based on left_motor.py and right_motor.py)
        driver.set_motor_mapping(left_id=2, right_id=3)

        # Apply speed correction if available
        speed_corr = config.get('speed_correction', {})
        left_scale = speed_corr.get('left_scale', 1.0)
        right_scale = speed_corr.get('right_scale', 1.0)
        if left_scale != 1.0 or right_scale != 1.0:
            logger.info(f"Applying speed correction: Left={left_scale}, Right={right_scale}")
            driver.reconfig_speed_correction(left_scale, right_scale)

    except Exception as e:
        logger.error(f"Failed to initialize ChassisDriver: {e}")
        return

    try:
        # 1. Clockwise Rotation
        # Angular velocity < 0 implies clockwise rotation (Left Forward, Right Backward)
        # Speed: 0 m/s linear, -1.5 rad/s angular
        logger.info("\n1. Testing Clockwise Rotation (Spin Right)...")
        logger.info("   Action: Left Wheels Forward, Right Wheels Backward")
        logger.info("   Sending: Linear=0 m/s, Angular=-1.5 rad/s")
        driver.rotate(-1.5)
        time.sleep(3)
        
        logger.info("   Stopping...")
        driver.stop()
        time.sleep(1)

        # 2. Counter-Clockwise Rotation
        # Angular velocity > 0 implies counter-clockwise rotation (Left Backward, Right Forward)
        # Speed: 0 m/s linear, 1.5 rad/s angular
        logger.info("\n2. Testing Counter-Clockwise Rotation (Spin Left)...")
        logger.info("   Action: Left Wheels Backward, Right Wheels Forward")
        logger.info("   Sending: Linear=0 m/s, Angular=1.5 rad/s")
        driver.rotate(1.5)
        time.sleep(3)
        
        logger.info("   Stopping...")
        driver.stop()
        time.sleep(1)

    except KeyboardInterrupt:
        logger.warning("\nTest interrupted by user. Stopping chassis...")
        driver.stop()
    except Exception as e:
        logger.error(f"An error occurred during rotation test: {e}")
        driver.stop()
    finally:
        logger.info("Closing Chassis Driver...")
        driver.close()

def main():
    """Main function to execute all chassis tests."""
    try:
        # Phase 1: Individual Motors
        test_individual_wheels()
        
        # Phase 2: Combined Rotation
        test_chassis_rotation()
        
        logger.info("\n" + "="*50)
        logger.info("All Chassis Tests Completed.")
        logger.info("="*50)
        
    except KeyboardInterrupt:
        logger.warning("Global test interrupted.")

if __name__ == "__main__":
    main()

