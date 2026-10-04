#!/usr/bin/env python3
import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TransformStamped, Quaternion
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster

# 使用标准的包导入方式
from support.driver.chassis_driver import ChassisDriver

class ChassisNode(Node):
    def __init__(self):
        super().__init__('chassis_node')
        
        # Parameters
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('publish_tf', True)
        self.declare_parameter('control_rate', 20.0) # Hz
        
        self.base_frame = self.get_parameter('base_frame').value
        self.odom_frame = self.get_parameter('odom_frame').value
        self.publish_tf_flag = self.get_parameter('publish_tf').value
        self.rate = self.get_parameter('control_rate').value
        
        # Initialize Chassis Driver
        try:
            self.driver = ChassisDriver()
            self.get_logger().info("Chassis Driver Initialized Successfully")
        except Exception as e:
            self.get_logger().error(f"Failed to initialize Chassis Driver: {e}")
            raise e

        # Publishers & Subscribers
        self.cmd_sub = self.create_subscription(
            Twist,
            '~/cmd_vel',
            self.cmd_vel_callback,
            10
        )
        
        self.odom_pub = self.create_publisher(Odometry, '~/odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self)
        
        # Odometry State
        self.x = 0.0
        self.y = 0.0
        self.th = 0.0
        self.last_time = self.get_clock().now()
        
        # Timer for Odom Loop
        self.create_timer(1.0 / self.rate, self.update_odom)
        
        self.get_logger().info("Chassis Node Started")

    def cmd_vel_callback(self, msg: Twist):
        linear_x = msg.linear.x
        angular_z = msg.angular.z
        
        # Send to driver
        self.driver.set_twist(linear_x, angular_z)

    def update_odom(self):
        current_time = self.get_clock().now()
        dt = (current_time - self.last_time).nanoseconds / 1e9
        self.last_time = current_time
        
        # Get wheel speeds from driver (m/s)
        # wheel_speed() returns (left_mps, right_mps)
        vl, vr = self.driver.wheel_speed()
        
        # Kinematics
        # v = (vr + vl) / 2
        # w = (vr - vl) / L
        
        L = self.driver.wheel_base_mm / 1000.0
        
        v = (vr + vl) / 2.0
        w = (vr - vl) / L
        
        # Integration (Dead Reckoning)
        delta_th = w * dt
        delta_x = v * math.cos(self.th) * dt
        delta_y = v * math.sin(self.th) * dt
        
        self.x += delta_x
        self.y += delta_y
        self.th += delta_th
        
        # Normalize theta
        # self.th = math.atan2(math.sin(self.th), math.cos(self.th)) 
        
        # Create Quaternion from Yaw
        q = self.quaternion_from_euler(0, 0, self.th)
        
        # Publish TF
        if self.publish_tf_flag:
            t = TransformStamped()
            t.header.stamp = current_time.to_msg()
            t.header.frame_id = self.odom_frame
            t.child_frame_id = self.base_frame
            t.transform.translation.x = self.x
            t.transform.translation.y = self.y
            t.transform.translation.z = 0.0
            t.transform.rotation = q
            self.tf_broadcaster.sendTransform(t)
            
        # Publish Odometry
        odom = Odometry()
        odom.header.stamp = current_time.to_msg()
        odom.header.frame_id = self.odom_frame
        odom.child_frame_id = self.base_frame
        
        # Pose
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.position.z = 0.0
        odom.pose.pose.orientation = q
        
        # Twist
        odom.twist.twist.linear.x = v
        odom.twist.twist.angular.z = w
        
        self.odom_pub.publish(odom)

    def quaternion_from_euler(self, roll, pitch, yaw):
        """
        Converts euler roll, pitch, yaw to geometry_msgs/Quaternion
        """
        qx = math.sin(roll/2) * math.cos(pitch/2) * math.cos(yaw/2) - math.cos(roll/2) * math.sin(pitch/2) * math.sin(yaw/2)
        qy = math.cos(roll/2) * math.sin(pitch/2) * math.cos(yaw/2) + math.sin(roll/2) * math.cos(pitch/2) * math.sin(yaw/2)
        qz = math.cos(roll/2) * math.cos(pitch/2) * math.sin(yaw/2) - math.sin(roll/2) * math.sin(pitch/2) * math.cos(yaw/2)
        qw = math.cos(roll/2) * math.cos(pitch/2) * math.cos(yaw/2) + math.sin(roll/2) * math.sin(pitch/2) * math.sin(yaw/2)
        return Quaternion(x=qx, y=qy, z=qz, w=qw)
        
    def destroy_node(self):
        self.driver.stop()
        self.driver.close()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = ChassisNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
