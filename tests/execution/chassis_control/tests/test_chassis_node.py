
import unittest
from unittest.mock import MagicMock, patch
import sys
import math
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parents[4]
sys.path.insert(0, str(PROJECT_ROOT))

import rclpy
from geometry_msgs.msg import Twist
from src.execution.chassis_control.chassis_node import ChassisNode

class TestChassisNode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()

    def setUp(self):
        # Patch the ChassisDriver class
        self.patcher = patch('src.execution.chassis_control.chassis_node.ChassisDriver')
        self.MockDriver = self.patcher.start()
        
        # Setup mock driver instance
        self.mock_driver_instance = self.MockDriver.return_value
        self.mock_driver_instance.wheel_base_mm = 160.0 # Default value
        self.mock_driver_instance.wheel_speed.return_value = (0.0, 0.0)
        
        # Initialize Node
        self.node = ChassisNode()

    def tearDown(self):
        self.node.destroy_node()
        self.patcher.stop()

    def test_initialization(self):
        """Test if node initializes and connects to driver"""
        self.MockDriver.assert_called_once()
        self.assertIsNotNone(self.node.driver)

    def test_cmd_vel_callback(self):
        """Test if Twist messages are forwarded to driver"""
        msg = Twist()
        msg.linear.x = 0.5
        msg.angular.z = 1.0
        
        self.node.cmd_vel_callback(msg)
        
        # Verify set_twist was called with correct args
        self.mock_driver_instance.set_twist.assert_called_with(0.5, 1.0)

    def test_odom_calculation_straight(self):
        """Test odometry calculation for straight line motion"""
        # Simulate 0.1s time step (approximate, since we call update_odom manually)
        # We need to mock time or just check the math logic
        
        # Mock wheel speeds: 1.0 m/s both wheels
        self.mock_driver_instance.wheel_speed.return_value = (1.0, 1.0)
        
        # Manually trigger update_odom
        # We need to sleep a bit to ensure dt > 0
        import time
        time.sleep(0.1)
        
        self.node.update_odom()
        
        # Check if X increased (v=1.0, dt~0.1 => dx~0.1)
        self.assertGreater(self.node.x, 0.0)
        self.assertAlmostEqual(self.node.y, 0.0)
        self.assertAlmostEqual(self.node.th, 0.0)

    def test_odom_calculation_rotation(self):
        """Test odometry calculation for in-place rotation"""
        # Mock wheel speeds: left=-0.5, right=0.5 (Spin Right/CCW positive? Wait.)
        # w = (vr - vl) / L
        # if vr=0.5, vl=-0.5, L=0.16 => w = (0.5 - (-0.5))/0.16 = 1.0/0.16 = 6.25 rad/s
        
        self.mock_driver_instance.wheel_speed.return_value = (-0.5, 0.5)
        
        import time
        time.sleep(0.1)
        
        self.node.update_odom()
        
        # Check if Theta increased
        self.assertGreater(self.node.th, 0.0)
        self.assertAlmostEqual(self.node.x, 0.0, delta=0.01) # Small movement due to integration approx
        self.assertAlmostEqual(self.node.y, 0.0, delta=0.01)

if __name__ == '__main__':
    unittest.main()
