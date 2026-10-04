#!/bin/bash
# Install dependencies for OrbbecSDK_ROS2
# Reference: https://github.com/orbbec/OrbbecSDK_ROS2

echo "Installing OrbbecSDK_ROS2 dependencies..."
sudo apt-get update
sudo apt-get install -y libgflags-dev nlohmann-json3-dev \
ros-humble-image-transport ros-humble-image-transport-plugins ros-humble-compressed-image-transport \
ros-humble-image-publisher ros-humble-camera-info-manager \
ros-humble-diagnostic-updater ros-humble-diagnostic-msgs ros-humble-statistics-msgs ros-humble-xacro \
ros-humble-backward-ros libdw-dev libssl-dev mesa-utils libgl1 libgoogle-glog-dev

echo "Dependencies installed."

echo "Cloning LDS50C_SDK..."
if [ ! -d "src/support/sdk/LDS50C_SDK" ]; then
    git clone https://github.com/BlueSeaLidar/sdk2.git src/support/sdk/LDS50C_SDK
else
    echo "LDS50C_SDK already exists."
fi

echo "Cloning OrbbecSDK_ROS2..."
if [ ! -d "src/support/sdk/OrbbecSDK_ROS2" ]; then
    git clone https://github.com/orbbec/OrbbecSDK_ROS2.git src/support/sdk/OrbbecSDK_ROS2
else
    echo "OrbbecSDK_ROS2 already exists."
fi