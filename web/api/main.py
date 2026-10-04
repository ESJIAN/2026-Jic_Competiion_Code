import sys
import os
import yaml
import time

from pathlib import Path
from fastapi import FastAPI, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]

from program.src.support.driver.chassis_driver import ChassisDriver
from program.src.support.driver.imu_driver import IMUDriver
from program.src.support.driver.lidar_driver import LidarDriver
from program.src.support.driver.camera_driver import CameraDriver
from program.src.support.logger import get_logger

logger = get_logger("web_api")

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


CONFIG_PATH = PROJECT_ROOT / 'config/chasis_params.yaml'
driver = None
imu_driver = None
lidar_driver = None
camera_driver = None

def get_driver():
    global driver
    if driver is None:
        try:
            driver = ChassisDriver()
        except Exception as e:
            logger.error(f"Failed to initialize chassis driver: {e}")
    return driver

def get_imu_driver():
    global imu_driver
    if imu_driver is None:
        try:
            imu_driver = IMUDriver()
        except Exception as e:
            logger.error(f"Failed to initialize IMU driver: {e}")
    return imu_driver

def get_lidar_driver():
    global lidar_driver
    if lidar_driver is None:
        try:
            lidar_driver = LidarDriver()
        except Exception as e:
            logger.error(f"Failed to initialize LiDAR driver: {e}")
    return lidar_driver

def get_camera_driver():
    global camera_driver
    if camera_driver is None:
        try:
            camera_driver = CameraDriver()
        except Exception as e:
            logger.error(f"Failed to initialize Camera driver: {e}")
    return camera_driver

class SpeedCorrection(BaseModel):
    left_scale: float
    right_scale: float

class ControlCommand(BaseModel):
    action: str  # "rotate_cw", "rotate_ccw", "stop"
    linear_speed: float = 0.5
    angular_speed: float = 1.5

@app.get("/api/config")
async def get_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
            return config.get('speed_correction', {'left_scale': 1.0, 'right_scale': 1.0})
    return {'left_scale': 1.0, 'right_scale': 1.0}

@app.post("/api/config")
async def update_config(correction: SpeedCorrection):
    if not CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail="Config file not found")
    
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f) or {}
        
        config['speed_correction'] = {
            'left_scale': correction.left_scale,
            'right_scale': correction.right_scale
        }
        
        with open(CONFIG_PATH, 'w') as f:
            yaml.dump(config, f)
            
        # Update driver if active
        d = get_driver()
        if d:
            d.reconfig_speed_correction(correction.left_scale, correction.right_scale)
            
        return {"status": "success", "config": config['speed_correction']}
    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/control")
async def control_chassis(cmd: ControlCommand):
    d = get_driver()
    if not d:
        raise HTTPException(status_code=500, detail="Chassis driver not initialized")
    
    try:
        # Re-apply current config to ensure scales are up to date
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
            sc = config.get('speed_correction', {})
            d.reconfig_speed_correction(sc.get('left_scale', 1.0), sc.get('right_scale', 1.0))

        if cmd.action == "rotate_cw":
            # Clockwise: Left Forward, Right Backward
            # Angular < 0
            d.rotate(-abs(cmd.angular_speed))
        elif cmd.action == "rotate_ccw":
            # Counter-Clockwise: Left Backward, Right Forward
            # Angular > 0
            d.rotate(abs(cmd.angular_speed))
        elif cmd.action == "move_forward":
            # Move Forward: Linear > 0
            d.move(abs(cmd.linear_speed))
        elif cmd.action == "move_backward":
            # Move Backward: Linear < 0
            d.move(-abs(cmd.linear_speed))
        elif cmd.action == "stop":
            d.stop()
        else:
            return {"status": "error", "message": "Unknown action"}
            
        return {"status": "success", "action": cmd.action}
    except Exception as e:
        logger.error(f"Control failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/battery")
async def get_battery_info():
    d = get_driver()
    if not d:
        raise HTTPException(status_code=500, detail="Chassis driver not initialized")
    try:
        voltage = d.battery_voltage()
        return {"voltage": voltage}
    except Exception as e:
        logger.error(f"Failed to get battery info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chassis/speed")
async def get_wheel_speed():
    d = get_driver()
    if not d:
        raise HTTPException(status_code=500, detail="Chassis driver not initialized")
    try:
        left_speed, right_speed = d.wheel_speed()
        return {"left_speed": left_speed, "right_speed": right_speed}
    except Exception as e:
        logger.error(f"Failed to get wheel speed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/imu")
async def get_imu_data():
    d = get_imu_driver()
    if not d:
        raise HTTPException(status_code=500, detail="IMU driver not initialized")
    try:
        return d.get_data()
    except Exception as e:
        logger.error(f"Failed to get IMU data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/lidar")
async def get_lidar_data():
    d = get_lidar_driver()
    if not d:
        raise HTTPException(status_code=500, detail="LiDAR driver not initialized")
    try:
        return d.get_scan()
    except Exception as e:
        logger.error(f"Failed to get LiDAR data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/camera/stream")
async def video_feed():
    def generate():
        cam = get_camera_driver()
        if not cam:
            return
        
        while True:
            frame = cam.get_jpeg_frame()
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            else:
                time.sleep(0.1) # Wait if no frame
            time.sleep(0.01) # Small delay to prevent CPU hogging

    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")

# Mount static files
app.mount("/", StaticFiles(directory=str(PROJECT_ROOT / "web/public"), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
