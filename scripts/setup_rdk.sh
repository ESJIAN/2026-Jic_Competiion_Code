#!/bin/bash
# ==========================================
# RDK X5 ROS2 通信配置脚本 (RDK IP: 10.70.90.52)
# ==========================================

# 1. 定义对方 (Windows 宿主机) 的 IP
WIN_IP="10.70.90.197"

# 2. 生成 FastDDS 配置文件
cat <<EOF > ~/fastdds_rdk_cfg.xml
<?xml version="1.0" encoding="UTF-8" ?>
<profiles xmlns="http://www.eprosima.com/XMLSchemas/fastrtps_profiles">
    <participant profile_name="rdk_participant" is_default_profile="true">
        <rtps>
            <builtin>
                <initialPeersList>
                    <locator>
                        <udpv4>
                            <address>$WIN_IP</address>
                        </udpv4>
                    </locator>
                </initialPeersList>
            </builtin>
        </rtps>
    </participant>
</profiles>
EOF

# 3. 设置 ROS2 环境变量
export FASTRTPS_DEFAULT_PROFILES_FILE=~/fastdds_rdk_cfg.xml
export ROS_DOMAIN_ID=10
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp

# 针对精简版系统，强制重启守护进程
ros2 daemon stop && ros2 daemon start

echo "✅ RDK X5 配置完成！"
echo "📍 已指向 Windows IP: $WIN_IP"
echo "🚀 ROS2 Daemon 已重启"