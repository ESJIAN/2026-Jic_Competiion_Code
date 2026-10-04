#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    interaction_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            get_package_share_directory('bci_mr_interaction'), 'launch', 'interaction.launch.py'])
    )
    task_planner_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            get_package_share_directory('task_planner'), 'launch', 'task_planner.launch.py'])
    )
    return LaunchDescription([
        interaction_launch,
        task_planner_launch
    ])
