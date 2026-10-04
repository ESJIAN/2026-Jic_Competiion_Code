#!/usr/bin/env python3

from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # 这里添加启动节点的配置，例如:
        # Node(
        #     package='path_planning',
        #     executable='nav2_adapter',
        #     name='nav2_adapter_node'
        # )
    ])
