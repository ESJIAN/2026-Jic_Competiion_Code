#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu

# [规范建议] 尽量避免使用 'src.xxx' 这种路径。
# 如果 support 是另一个 ROS 包，应该通过 colcon 依赖来解决。
# 如果 support 是这个包的一部分，应该调整文件夹结构。
# 暂时保留你的写法，但请注意这是非标准的。
from src.support.driver.imu_driver import IMUDriver

class ImuNode(Node):
    def __init__(self):
        super().__init__('imu_node')
        
        # [规范] 参数声明是很好的实践
        self.declare_parameter('frame_id', 'imu_link')
        self.declare_parameter('pub_rate', 100.0)
        
        self.frame_id = self.get_parameter('frame_id').value
        self.rate = self.get_parameter('pub_rate').value
        
        # [规范] 硬件初始化最好放在这里的 try-except 块中
        try:
            self.driver = IMUDriver()
            if not self.driver.connected:
                self.get_logger().error("IMU Driver reports not connected.")
                # [建议] 初始化失败时，是退出还是重试？通常建议抛出异常让生命周期管理或系统重启节点
                raise RuntimeError("Hardware not connected")
            else:
                self.get_logger().info("IMU Driver Initialized Successfully")
        except Exception as e:
            self.get_logger().error(f"Failed to initialize IMU Driver: {e}")
            raise e

        # [规范] 使用 QoS Profile 使通信更可靠 (可选，但在传感器数据中常用)
        from rclpy.qos import QoSProfile, ReliabilityPolicy
        qos_profile = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        
        self.imu_pub = self.create_publisher(Imu, '~/data', qos_profile)
        
        # [新增] 用于记录校准状态，避免重复打印
        self.last_calibration = None
        self.calib_log_interval = 5.0  # 每 5 秒检查一次校准状态变化
        self.last_calib_log_time = self.get_clock().now()

        self.timer = self.create_timer(1.0 / self.rate, self.timer_callback)
        self.get_logger().info(f"IMU Node Started, rate: {self.rate}Hz")

    def log_calibration_status(self, calib):
        """记录传感器校准状态 (sys, gyro, accel, mag: 0-3)"""
        now = self.get_clock().now()
        if calib == self.last_calibration and (now - self.last_calib_log_time).nanoseconds < self.calib_log_interval * 1e9:
            return
        
        self.last_calibration = calib
        self.last_calib_log_time = now
        log_msg = f"Calibration Status: SYS={calib['sys']}, GYRO={calib['gyro']}, ACCEL={calib['accel']}, MAG={calib['mag']}"
        
        if all(v == 3 for v in calib.values()):
            self.get_logger().info(f"IMU Fully Calibrated: {log_msg}")
        else:
            self.get_logger().info(f"IMU Calibrating... {log_msg}")

    def timer_callback(self):
        try:
            data = self.driver.get_data()
        except Exception as e:
            self.get_logger().warn(f"Error reading hardware: {e}")
            return
        
        if data is None:
            return

        # [新增] 检查并打印校准状态
        if 'calibration' in data:
            self.log_calibration_status(data['calibration'])

        msg = Imu()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        
        # [优化] 使用字典的 .get 方法防止 KeyError 崩溃
        orient = data.get('orientation', {})
        msg.orientation.x = float(orient.get('x', 0.0))
        msg.orientation.y = float(orient.get('y', 0.0))
        msg.orientation.z = float(orient.get('z', 0.0))
        msg.orientation.w = float(orient.get('w', 1.0)) # w 默认为 1 防止无效四元数
        
        ang = data.get('angular_velocity', {})
        msg.angular_velocity.x = float(ang.get('x', 0.0))
        msg.angular_velocity.y = float(ang.get('y', 0.0))
        msg.angular_velocity.z = float(ang.get('z', 0.0))
        
        acc = data.get('linear_acceleration', {})
        msg.linear_acceleration.x = float(acc.get('x', 0.0))
        msg.linear_acceleration.y = float(acc.get('y', 0.0))
        msg.linear_acceleration.z = float(acc.get('z', 0.0))
        
        # [规范] 填充协方差矩阵 (Covariance Matrices)
        # 全 0 会导致 EKF 等滤波器报错或忽略数据。此处提供合理的初始估计值。
        msg.orientation_covariance = [
            0.01, 0.0,  0.0,
            0.0,  0.01, 0.0,
            0.0,  0.0,  0.01
        ]
        msg.angular_velocity_covariance = [
            0.001, 0.0,  0.0,
            0.0,   0.001, 0.0,
            0.0,   0.0,   0.001
        ]
        msg.linear_acceleration_covariance = [
            0.1, 0.0, 0.0,
            0.0, 0.1, 0.0,
            0.0, 0.0, 0.1
        ]
        
        self.imu_pub.publish(msg)

# [规范] 必须包含 main 函数供 entry_points 调用
def main(args=None):
    rclpy.init(args=args)
    node = ImuNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        # 这里使用 node.get_logger 可能会因为 node 销毁而出错，使用 print 或 logging 模块更安全
        print(f"Node execution failed: {e}")
    finally:
        # 确保销毁顺序
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()

if __name__ == '__main__':
    main()