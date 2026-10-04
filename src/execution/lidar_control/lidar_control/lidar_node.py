"""
Lidar Node for ROS 2.
Supports LDS-50C(Default) and RPLidar A/S series.
Features: Auto-reconnection, Dynamic parameters, Angle masking, and Event-driven publishing.
"""

import sys
import threading
import time
import math
import serial
import yaml
from enum import Enum
from pathlib import Path

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult

try:
    from rplidar import RPLidar, RPLidarException
except ImportError:
    RPLidar = None
    class RPLidarException(Exception):
        pass

# 使用标准的包导入方式
from program.src.support.driver.lidar_driver import LDS50CDriver

# Project Root for config loading
PROJECT_ROOT = Path(__file__).parents[4]

class NodeState(Enum):
    DISCONNECTED = 0
    CONNECTING = 1
    SCANNING = 2
    ERROR = 3

class LidarNode(Node):
    def __init__(self):
        super().__init__('lidar_node')
        
        # --- Parameters ---
        self.declare_parameter('serial_port', '/dev/ttyS1')
        self.declare_parameter('serial_baudrate', 500000)
        self.declare_parameter('lidar_type', 'LDS-50C') # Added lidar_type
        self.declare_parameter('frame_id', 'laser_frame')
        self.declare_parameter('inverted', False)
        self.declare_parameter('angle_compensate', True)
        self.declare_parameter('scan_mode', 'Standard')
        self.declare_parameter('channel_type', 'serial')
        self.declare_parameter('use_mock', False)
        
        # Angle masking (degrees)
        self.declare_parameter('mask_angle_start', 0.0) 
        self.declare_parameter('mask_angle_end', 0.0)   # If start == end, no mask
        self.load_parameters()
        self.add_on_set_parameters_callback(self.on_parameter_change)

        # --- Internal State ---
        self.state = NodeState.DISCONNECTED
        self.lidar = None
        self.scan_data = [float('inf')] * 360
        self.running = True
        self.lock = threading.Lock()
        self.scan_pub = self.create_publisher(LaserScan, '~/scan', 10)
        
        # --- Threads ---
        self.scan_thread = threading.Thread(target=self.main_loop)
        self.scan_thread.daemon = True
        self.scan_thread.start()

    def load_parameters(self):
        # --- Default Values ---
        defaults = {
            'serial_port': '/dev/ttyS1',
            'serial_baudrate': 500000,
            'lidar_type': 'LDS-50C',
            'frame_id': 'laser_frame',
            'inverted': False,
            'angle_compensate': True,
            'scan_mode': 'Standard',
            'channel_type': 'serial',
            'use_mock': False,
            'mask_angle_start': 0.0,
            'mask_angle_end': 0.0
        }
        
        # --- Load from YAML config file ---
        config_path = PROJECT_ROOT / 'config' / 'lidar_params.yaml'
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    if config and 'LDS50C' in config:
                        cfg = config['LDS50C']
                        # Map YAML keys to parameter names if different
                        yaml_mapping = {
                            'port': 'serial_port',
                            'baudrate': 'serial_baudrate'
                        }
                        for yaml_key, value in cfg.items():
                            param_key = yaml_mapping.get(yaml_key, yaml_key)
                            if param_key in defaults:
                                defaults[param_key] = value
                        self.get_logger().info(f"Loaded config from {config_path}")
            except Exception as e:
                self.get_logger().error(f"Failed to load config from {config_path}: {e}")

        # --- Set parameters with precedence: Command line > YAML > Defaults ---
        self.serial_port = self.get_parameter_or('serial_port', 
                                              rclpy.parameter.Parameter('serial_port', rclpy.Parameter.Type.STRING, defaults['serial_port'])).value
        self.serial_baudrate = self.get_parameter_or('serial_baudrate',
                                                   rclpy.parameter.Parameter('serial_baudrate', rclpy.Parameter.Type.INTEGER, defaults['serial_baudrate'])).value
        self.lidar_type = self.get_parameter_or('lidar_type',
                                              rclpy.parameter.Parameter('lidar_type', rclpy.Parameter.Type.STRING, defaults['lidar_type'])).value
        self.frame_id = self.get_parameter_or('frame_id',
                                            rclpy.parameter.Parameter('frame_id', rclpy.Parameter.Type.STRING, defaults['frame_id'])).value
        self.inverted = self.get_parameter_or('inverted',
                                            rclpy.parameter.Parameter('inverted', rclpy.Parameter.Type.BOOL, defaults['inverted'])).value
        self.angle_compensate = self.get_parameter_or('angle_compensate',
                                                   rclpy.parameter.Parameter('angle_compensate', rclpy.Parameter.Type.BOOL, defaults['angle_compensate'])).value
        self.scan_mode = self.get_parameter_or('scan_mode',
                                             rclpy.parameter.Parameter('scan_mode', rclpy.Parameter.Type.STRING, defaults['scan_mode'])).value
        self.channel_type = self.get_parameter_or('channel_type',
                                                rclpy.parameter.Parameter('channel_type', rclpy.Parameter.Type.STRING, defaults['channel_type'])).value
        self.use_mock = self.get_parameter_or('use_mock',
                                            rclpy.parameter.Parameter('use_mock', rclpy.Parameter.Type.BOOL, defaults['use_mock'])).value
        self.mask_angle_start = self.get_parameter_or('mask_angle_start',
                                                    rclpy.parameter.Parameter('mask_angle_start', rclpy.Parameter.Type.DOUBLE, float(defaults['mask_angle_start']))).value
        self.mask_angle_end = self.get_parameter_or('mask_angle_end',
                                                  rclpy.parameter.Parameter('mask_angle_end', rclpy.Parameter.Type.DOUBLE, float(defaults['mask_angle_end']))).value

    def on_parameter_change(self, params):
        for param in params:
            if param.name == 'inverted':
                self.inverted = param.value
            elif param.name == 'angle_compensate':
                self.angle_compensate = param.value
            elif param.name == 'use_mock':
                self.use_mock = param.value
            elif param.name == 'mask_angle_start':
                self.mask_angle_start = param.value
            elif param.name == 'mask_angle_end':
                self.mask_angle_end = param.value
        return SetParametersResult(successful=True)

    def is_angle_masked(self, angle):
        if self.mask_angle_start == self.mask_angle_end:
            return False
        
        # Handle wrap around
        if self.mask_angle_start < self.mask_angle_end:
            return self.mask_angle_start <= angle <= self.mask_angle_end
        else:
            return angle >= self.mask_angle_start or angle <= self.mask_angle_end

    def force_stop_lidar(self):
        """Send raw stop command to serial port to clear Lidar state."""
        try:
            self.get_logger().info(f"Force stopping Lidar on {self.serial_port} to clear buffer...")
            ser = serial.Serial(self.serial_port, self.serial_baudrate, timeout=1)
            # RPLidar STOP command is 0xA5 0x25
            ser.write(b'\xa5\x25')
            time.sleep(0.5)
            ser.close()
        except Exception as e:
            self.get_logger().warning(f"Could not force stop Lidar: {e}")

    def connect_lidar(self):
        try:
            self.state = NodeState.CONNECTING
            self.get_logger().info(f"Connecting to {self.lidar_type} on {self.serial_port} at {self.serial_baudrate}...")
            
            if self.lidar_type == 'LDS-50C':
                self.lidar = LDS50CDriver(self.serial_port, baudrate=self.serial_baudrate)
                if self.lidar.connect():
                    self.get_logger().info(f"Connected to LDS-50C")
                    self.state = NodeState.SCANNING
                    return True
                else:
                    return False
            else:
                # RPLidar logic
                if RPLidar is None:
                    self.get_logger().warning("RPLidar library not installed. Running in MOCK mode.")
                    return False
                
                self.force_stop_lidar()
                self.lidar = RPLidar(self.serial_port, baudrate=self.serial_baudrate, timeout=3)
                self.lidar.clear_input()
                info = self.lidar.get_info()
                health = self.lidar.get_health()
                self.get_logger().info(f"Connected. Info: {info}, Health: {health}")
                
                if health[0] == 'Error':
                    self.get_logger().error(f"Lidar health error: {health[1]}. Attempting reset.")
                    self.lidar.reset()
                    time.sleep(1)
                
                self.state = NodeState.SCANNING
                return True
        except Exception as e:
            err_msg = str(e)
            if "Incorrect descriptor starting bytes" in err_msg:
                self.get_logger().error(f"Failed to connect to Lidar: {err_msg}. "
                                 f"Suggestion: Check if baudrate {self.serial_baudrate} is correct for your Lidar model.")
            else:
                self.get_logger().error(f"Failed to connect to Lidar: {e}")
            
            self.state = NodeState.ERROR
            self.cleanup_lidar()
            return False

    def cleanup_lidar(self):
        if self.lidar:
            try:
                self.lidar.stop()
                self.lidar.stop_motor()
                self.lidar.disconnect()
            except:
                pass
            self.lidar = None
        self.state = NodeState.DISCONNECTED

    def main_loop(self):
        retry_delay = 1.0
        while self.running and rclpy.ok():
            if self.use_mock or RPLidar is None: # TODO: repair "RPLidar" is not defined
                self.mock_scan_loop()
                continue

            if self.state in [NodeState.DISCONNECTED, NodeState.ERROR]:
                if self.connect_lidar():
                    retry_delay = 1.0 # Reset delay on success
                else:
                    self.get_logger().info(f"Retrying connection in {retry_delay:.1f}s...")
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 30.0) # Exponential backoff
                    continue

            try:
                if self.lidar_type != 'LDS-50C':
                    self.lidar.start_motor()
                # Use iter_scans for event-driven data processing
                # For RPLidar, we can pass scan_mode
                iter_args = {}
                if self.lidar_type != 'LDS-50C' and self.scan_mode:
                    iter_args['scan_type'] = self.scan_mode
                
                for scan in self.lidar.iter_scans(**iter_args):
                    if not self.running or not rclpy.ok():
                        break
                    
                    self.process_scan(scan)
                    self.publish_scan()
                    
            except RPLidarException as e:
                self.get_logger().error(f"Lidar exception: {e}")
                self.state = NodeState.ERROR
            except Exception as e:
                self.get_logger().error(f"Unexpected error in scan loop: {e}")
                self.state = NodeState.ERROR
            finally:
                self.cleanup_lidar()

    def mock_scan_loop(self):
        while self.running and rclpy.ok():
            with self.lock:
                for i in range(360):
                    self.scan_data[i] = 2.0 + 0.1 * math.sin(time.time() + i * 0.1)
            self.publish_scan()
            time.sleep(0.1)

    def process_scan(self, scan):
        with self.lock:
            # We don't necessarily clear the whole array to maintain a persistence effect,
            # but for a fresh 360 scan, it's safer to rely on new data.
            # iter_scans usually provides one full rotation.
            
            for (_, angle, distance) in scan:
                if distance <= 0:
                    continue
                
                angle_deg = angle % 360
                if self.is_angle_masked(angle_deg):
                    dist_m = float('inf')
                else:
                    dist_m = distance / 1000.0 # mm to m
                
                angle_idx = int(angle_deg)
                if self.inverted:
                    self.scan_data[359 - angle_idx] = dist_m
                else:
                    self.scan_data[angle_idx] = dist_m

    def publish_scan(self):
        msg = LaserScan()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        
        msg.angle_min = 0.0
        msg.angle_max = 2.0 * math.pi
        msg.angle_increment = math.pi / 180.0
        msg.time_increment = 0.0 
        msg.scan_time = 0.1 # Approx 10Hz
        msg.range_min = 0.15
        msg.range_max = 12.0
        
        with self.lock:
            msg.ranges = list(self.scan_data)
            
        self.scan_pub.publish(msg)

    def destroy_node(self):
        self.get_logger().info("Shutting down Lidar Node...")
        self.running = False
        self.cleanup_lidar()
        if self.scan_thread.is_alive():
            self.scan_thread.join(timeout=2.0)
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = LidarNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
