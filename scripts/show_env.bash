#!/bin/bash

echo "============================================================"
echo " 🛠️  JIC Competition - Environment Status Check"
echo "============================================================"
echo "Timestamp: $(date)"
echo ""

echo "------------------- [1. System Hardware] -------------------"
echo "Model: $(cat /proc/device-tree/model 2>/dev/null || echo 'Unknown')"
echo "Kernel: $(uname -r)"
echo "CPU Architecture: $(uname -m)"
if command -v grep &> /dev/null; then
    echo "CPU Cores: $(grep -c ^processor /proc/cpuinfo)"
fi
echo ""
echo "--- Memory & Swap (Critical for Compilation) ---"
free -h
echo ""
echo "--- Disk Usage ---"
df -h / | awk 'NR==1 || NR==2'
echo ""

echo "------------------- [2. Software / ROS] --------------------"
if command -v ros2 &> /dev/null; then
    echo "ROS Distro: $ROS_DISTRO"
    echo "ROS Domain ID: $ROS_DOMAIN_ID"
    echo "Python for ROS: $(which python3)"
else
    echo "❌ ROS 2 not found in environment variables."
fi
echo ""

echo "------------------- [2.1 Compilers & Build Tools] ----------"
echo "GCC:     $(gcc --version | head -n 1 2>/dev/null || echo 'Not found')"
echo "G++:     $(g++ --version | head -n 1 2>/dev/null || echo 'Not found')"
echo "CMake:   $(cmake --version | head -n 1 2>/dev/null || echo 'Not found')"
echo "Make:    $(make --version | head -n 1 2>/dev/null || echo 'Not found')"
echo "Python3: $(python3 --version 2>/dev/null || echo 'Not found')"
echo ""

echo "------------------- [3. Project Settings] ------------------"
echo "Workspace Root: $PWD"
if [ -f "requirements.txt" ]; then
    echo "Dependencies: requirements.txt matches installed?"
    # Simple check if some key packages are installed
    pip list | grep -E "pyserial|smbus2" | awk '{print "  - "$1": "$2}'
else
    echo "⚠️  requirements.txt not found."
fi

echo "------------------- [4. RDK X5 Specific] -------------------"
if command -v hrut_somstatus &> /dev/null; then
    echo "Status Summary:"
    sudo hrut_somstatus --brief 2>/dev/null || echo "  (hrut_somstatus failed)"
    echo "Temprature:"
    cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null | awk '{print $1/1000 " C"}' || echo "N/A"
else
    echo "RDK Utilities (hrut_somstatus) not found."
fi

echo "============================================================"
