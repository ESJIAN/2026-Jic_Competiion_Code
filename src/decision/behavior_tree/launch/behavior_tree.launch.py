#!/usr/bin/env python3

from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # 这里添加启动节点的配置，例如:
        # Node(
        #     package='behavior_tree',
        #     executable='behavior_tree_node',
        #     name='behavior_tree_node'
        # )
    ])
