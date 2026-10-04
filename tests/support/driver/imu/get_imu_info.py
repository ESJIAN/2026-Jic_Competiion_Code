import sys
import os
import time



def test_imu():
    logger.info("Initializing IMU Driver...")
    # Try bus 5, default address 0x29
    imu = IMUDriver(bus_num=5, address=0x29)
    
    if imu.connected:
        logger.info("IMU Connected!")
        for _ in range(5):
            data = imu.get_data()
            logger.info(f"Data: {data}")
            time.sleep(1)
    else:
        logger.info("IMU Not Connected (Expected if no hardware)")  

if __name__ == "__main__":
    
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
    from program.src.support.driver.imu_driver import IMUDriver
    from program.src.support.logger import get_logger

    logger = get_logger(__name__)

    test_imu()
