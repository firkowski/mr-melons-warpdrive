from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def robot_description(share: Path) -> str:
    urdf = (share/'urdf/reactor.urdf').read_text()
    return urdf.replace('package://melon_warpdrive/', share.resolve().as_uri() + '/')


def generate_launch_description():
    share = Path(get_package_share_directory('melon_warpdrive'))
    return LaunchDescription([
        DeclareLaunchArgument('parameters_file', default_value=str(share/'config/reactor_params.yaml')),
        DeclareLaunchArgument('rviz', default_value='true'),
        Node(package='melon_warpdrive', executable='simulator', output='screen',
             parameters=[{'parameters_file': LaunchConfiguration('parameters_file')}]),
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[{'robot_description': ParameterValue(
                 robot_description(share), value_type=str)}]),
        Node(package='rviz2', executable='rviz2', arguments=['-d', str(share/'rviz/reactor.rviz')],
             condition=IfCondition(LaunchConfiguration('rviz'))),
    ])
