from glob import glob
from setuptools import setup

setup(
    name='melon_warpdrive', version='0.1.0', packages=['warpdrive'],
    python_requires='>=3.10',
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/melon_warpdrive']),
        ('share/melon_warpdrive', ['package.xml']),
        ('share/melon_warpdrive/launch', glob('launch/*.launch.py')),
        ('share/melon_warpdrive/urdf', glob('urdf/*.urdf')),
        ('share/melon_warpdrive/urdf/model', glob('urdf/model/*.stl')),
        ('share/melon_warpdrive/rviz', glob('rviz/*.rviz')),
        ('share/melon_warpdrive/config', ['config/reactor_params.yaml']),
    ],
    install_requires=['setuptools', 'numpy>=1.24,<3', 'PyYAML>=6,<7'],
    extras_require={'rl': ['gymnasium>=1.2,<1.4', 'stable-baselines3>=2.7,<3'],
                    'test': ['pytest>=8,<10'], 'plots': ['matplotlib>=3.7,<4']},
    entry_points={'console_scripts': ['simulator = warpdrive.sim_node:main', 'controller = warpdrive.policy_node:main']},
    maintainer='Max Firkowski', maintainer_email='mfirkowski@ethz.ch',
    description='CAD, reinforcement learning and ROS 2 Furuta pendulum assignment',
    license='MIT',
)
