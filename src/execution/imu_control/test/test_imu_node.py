import sys    
import rclpy
from rclpy.node import Node
from pathlib import Path

# In test_imu_node.# In test_imu_node.py
PROJECT_ROOT = Path(__file__).parents[4]
sys.path.insert(0, str(PROJECT_ROOT))
from src.execution.imu_control.imu_control import ImuNode

def main(args=None):
    rclpy.init(args=args)
    node = ImuNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"IMU Node Error: {e}")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()