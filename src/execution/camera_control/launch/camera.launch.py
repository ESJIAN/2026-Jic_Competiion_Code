from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # Package directories
    try:
        orbbec_camera_dir = get_package_share_directory('orbbec_camera')
    except:
        # If package not found (not built yet), handling gracefully?
        # In a build environment, this might fail if not sourced.
        print("Warning: orbbec_camera package not found.")
        return LaunchDescription([])

    # Launch arguments
    # Plan mentions 15-30Hz.
    
    camera_model = LaunchConfiguration('camera_model', default='gemini330_series')

    return LaunchDescription([
        DeclareLaunchArgument(
            'camera_model',
            default_value='gemini330_series',
            description='Camera model'
        ),
        
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(orbbec_camera_dir, 'launch', 'orbbec_camera.launch.py')
            ),
            launch_arguments={
                'camera_model': camera_model,
                'depth_registration': 'true',
                'publish_tf': 'true',
            }.items()
        )
    ])
