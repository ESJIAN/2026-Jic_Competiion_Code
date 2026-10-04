
import sys
import os
from pathlib import Path

from src.support.driver.camera_driver import CameraDriver
import cv2

def test_camera():
    from src.support.logger import logger
    logger.debug("Initializing CameraDriver...")
    cam = CameraDriver()
    
    logger.debug("Attempting to get frames...")
    for i in range(10):
        frame = cam.get_frame()
        if frame is not None:
            logger.debug(f"Frame {i} captured successfully. Shape: {frame.shape}")
            cv2.imwrite(f"test_capture_{i}.jpg", frame)
            logger.debug(f"Saved to test_capture_{i}.jpg")
        else:
            logger.debug(f"Failed to capture frame {i}")
        
    cam.close()

if __name__ == "__main__":
    test_camera()
