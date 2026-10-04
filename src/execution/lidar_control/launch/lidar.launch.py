import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    # --- YAML Config Path ---
    # In a real workspace, config might be in the package's share directory
    # But based on project structure, it's in the root /config folder
    config_file_path = '/app/jic_competiion/config/lidar_params.yaml'
    
    # --- Common Parameters ---
    serial_port = LaunchConfiguration('serial_port', default='/dev/ttyS1')
    serial_baudrate = LaunchConfiguration('serial_baudrate', default='500000')
    lidar_type = LaunchConfiguration('lidar_type', default='LDS-50C')
    frame_id = LaunchConfiguration('frame_id', default='laser_frame')
    inverted = LaunchConfiguration('inverted', default='false')
    angle_compensate = LaunchConfiguration('angle_compensate', default='true')
    
    # --- Additional Parameters (kept for compatibility/RPLidar) ---
    channel_type = LaunchConfiguration('channel_type', default='serial')
    scan_mode = LaunchConfiguration('scan_mode', default='Standard')

    return LaunchDescription([
        # Declare arguments
        DeclareLaunchArgument(
            'serial_port',
            default_value=serial_port,
            description='Specifying usb port to connected lidar'),

        DeclareLaunchArgument(
            'serial_baudrate',
            default_value=serial_baudrate,
            description='Specifying usb port baudrate to connected lidar'),
        
        DeclareLaunchArgument(
            'lidar_type',
            default_value=lidar_type,
            description='Lidar type (LDS-50C or RPLidar)'),
        
        DeclareLaunchArgument(
            'frame_id',
            default_value=frame_id,
            description='Specifying frame_id of lidar'),

        DeclareLaunchArgument(
            'inverted',
            default_value=inverted,
            description='Specifying whether or not to invert scan data'),

        DeclareLaunchArgument(
            'angle_compensate',
            default_value=angle_compensate,
            description='Specifying whether or not to enable angle_compensate of scan data'),

        DeclareLaunchArgument(
            'channel_type',
            default_value=channel_type,
            description='Specifying channel type of lidar (serial or tcp)'),

        DeclareLaunchArgument(
            'scan_mode',
            default_value=scan_mode,
            description='Specifying scan mode of lidar'),

        # Run lidar_node from lidar_control package
        Node(
            package='lidar_control',
            executable='lidar_node',
            name='lidar_node',
            parameters=[
                config_file_path, # Load parameters from YAML file
                {
                    'serial_port': serial_port,
                    'serial_baudrate': serial_baudrate,
                    'lidar_type': lidar_type,
                    'frame_id': frame_id,
                    'inverted': inverted,
                    'angle_compensate': angle_compensate,
                    'scan_mode': scan_mode,
                    'channel_type': channel_type
                }
            ],
            output='screen'),
    ])
