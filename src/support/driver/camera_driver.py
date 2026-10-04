import cv2
import threading
import time
from src.support.logger import get_logger

logger = get_logger("camera_driver")

class CameraDriver:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None
        self.lock = threading.Lock()
        self.is_opened = False

    def open(self):
        with self.lock:
            if self.is_opened:
                return True
            try:
                self.cap = cv2.VideoCapture(self.camera_index)
                if not self.cap.isOpened():
                    logger.error(f"Failed to open camera {self.camera_index}")
                    return False
                
                # Set resolution to 640x480 for better streaming performance
                # Note: Setting these properties might fail on some cameras/drivers
                # self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                # self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                # self.cap.set(cv2.CAP_PROP_FPS, 30)
                
                self.is_opened = True
                logger.debug(f"Camera {self.camera_index} opened successfully") 
                return True
            except Exception as e:
                logger.error(f"Error opening camera: {e}")
                return False

    def close(self):
        with self.lock:
            if self.cap and self.is_opened:
                self.cap.release()
                self.is_opened = False
                logger.info("Camera closed")

    def get_frame(self):
        if not self.is_opened:
            if not self.open():
                return None
        
        with self.lock:
            if self.cap and self.is_opened:
                ret, frame = self.cap.read()
                if ret:
                    return frame
                else:
                    logger.debug("Failed to read frame")
                    return None
            return None

    def get_jpeg_frame(self):
        frame = self.get_frame()
        if frame is not None:
            ret, jpeg = cv2.imencode('.jpg', frame)
            if ret:
                return jpeg.tobytes()
        return None
